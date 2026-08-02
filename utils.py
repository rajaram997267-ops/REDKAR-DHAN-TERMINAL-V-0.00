"""
utils.py (Dhan Cloud project file)

All Dhan API + Postgres logic for the live-trading leg of Rajaram Trading
Terminal. Runs on Dhan Cloud's own infrastructure, so calls to Dhan's
trading/data API need no IP whitelisting - this is the whole point of
moving this piece off Render.

Expected Dhan Cloud Env Variables (set in the Env Variables tab):
    DHAN_CLIENT_ID
    DHAN_ACCESS_TOKEN
    DATABASE_URL          (same Neon connection string Render uses)

Expected Dependencies (set in the Dependencies tab):
    psycopg2-binary
    requests

CONFIRM BEFORE LIVE USE: the scrip-master CSV column names (SEM_*) and the
option-chain JSON field names below are my best-documented guess - I could
not verify them against a live raw-JSON response (I only had access to a
formatted-text MCP tool, not raw REST). Run debug_instruments() once
(print its output, or write it to a debug table) after your first deploy
and fix any names here if matched counts come back 0.
"""

import csv
import io
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras

IST_OFFSET = timedelta(hours=5, minutes=30)
DHAN_BASE_URL = "https://api.dhan.co/v2"
DHAN_SCRIP_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"


def get_db():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    return conn


def db_execute(conn, query, params=None):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params or ())
    return cur


def _headers():
    return {
        "access-token": os.environ["DHAN_ACCESS_TOKEN"],
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Instrument master - loaded fresh each run (Dhan Cloud runs are short-lived
# scheduled invocations, so there's no long-lived process to cache across
# minutes; a ~few-second CSV download once per run is an acceptable cost)
# ---------------------------------------------------------------------------

def load_instrument_master():
    req = urllib.request.Request(DHAN_SCRIP_MASTER_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_bytes = resp.read()
    text = raw_bytes.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    equity_map = {}
    option_chains = {}
    for row in reader:
        exch = (row.get("SEM_EXM_EXCH_ID") or "").upper()
        instr = (row.get("SEM_INSTRUMENT_NAME") or "").upper()
        sec_id = row.get("SEM_SMST_SECURITY_ID")
        tsym = (row.get("SEM_TRADING_SYMBOL") or "").upper()

        if exch == "NSE" and instr == "EQUITY" and tsym and sec_id:
            equity_map[tsym] = sec_id
        elif instr in ("OPTSTK", "OPTIDX") and sec_id:
            opt_type = (row.get("SEM_OPTION_TYPE") or "").upper()
            if opt_type not in ("CE", "PE"):
                continue
            underlying = (
                row.get("SEM_UNDERLYING_SYMBOL")
                or row.get("SEM_TRADING_SYMBOL", "").split("-")[0]
                or ""
            ).upper()
            try:
                strike = float(row.get("SEM_STRIKE_PRICE") or 0) or None
            except (TypeError, ValueError):
                strike = None
            try:
                lot_size = int(float(row.get("SEM_LOT_UNITS") or 0)) or None
            except (TypeError, ValueError):
                lot_size = None
            expiry = (row.get("SEM_EXPIRY_DATE") or "")[:10] or None

            if underlying and strike and expiry and lot_size and sec_id:
                option_chains.setdefault(underlying, []).append({
                    "strike": strike, "opt_type": opt_type, "expiry": expiry,
                    "security_id": sec_id, "lot_size": lot_size,
                })
    return equity_map, option_chains


def get_atm_option(option_chains: dict, symbol: str, opt_type: str, reference_price: float):
    """Same nearest-monthly-expiry + closest-strike logic as your existing
    get_atm_option()."""
    today = (datetime.utcnow() + IST_OFFSET).strftime("%Y-%m-%d")
    contracts = option_chains.get((symbol or "").upper())
    if not contracts:
        return None
    all_expiries = sorted({c["expiry"] for c in contracts if c["expiry"] >= today})
    if not all_expiries:
        return None
    monthly_by_month = {}
    for exp in all_expiries:
        mk = exp[:7]
        if mk not in monthly_by_month or exp > monthly_by_month[mk]:
            monthly_by_month[mk] = exp
    nearest_monthly = min(monthly_by_month.values())
    candidates = [c for c in contracts if c["expiry"] == nearest_monthly and c["opt_type"] == opt_type]
    if not candidates:
        return None
    return min(candidates, key=lambda c: abs(c["strike"] - reference_price))


def get_available_funds():
    req = urllib.request.Request(f"{DHAN_BASE_URL}/fundlimit", headers=_headers())
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())
    return float(payload.get("availabelBalance", payload.get("availableBalance", 0)))


def get_ltp(security_id: str, exchange_segment: str = "NSE_FNO"):
    body = {exchange_segment: [int(security_id)]}
    req = urllib.request.Request(
        f"{DHAN_BASE_URL}/marketfeed/ltp", data=json.dumps(body).encode(),
        method="POST", headers=_headers(),
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode())
    data = (payload.get("data") or {}).get(exchange_segment) or {}
    entry = data.get(str(security_id)) or {}
    return entry.get("last_price")


def fetch_5min_candles(security_id: str, exchange_segment: str = "NSE_FNO", instrument: str = "OPTSTK"):
    now_ist = datetime.utcnow() + IST_OFFSET
    from_dt = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    body = {
        "securityId": str(security_id), "exchangeSegment": exchange_segment,
        "instrument": instrument, "interval": 5, "oi": False,
        "fromDate": from_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
    }
    req = urllib.request.Request(
        f"{DHAN_BASE_URL}/charts/intraday", data=json.dumps(body).encode(),
        method="POST", headers=_headers(),
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())
    return list(zip(payload.get("open", []), payload.get("high", []),
                     payload.get("low", []), payload.get("close", [])))


def place_order(security_id: str, transaction_type: str, quantity: int):
    body = {
        "dhanClientId": os.environ["DHAN_CLIENT_ID"],
        "transactionType": transaction_type,
        "exchangeSegment": "NSE_FNO",
        "productType": "MARGIN",
        "orderType": "MARKET",
        "validity": "DAY",
        "securityId": str(security_id),
        "quantity": quantity,
        "price": 0,
    }
    req = urllib.request.Request(
        f"{DHAN_BASE_URL}/orders", data=json.dumps(body).encode(),
        method="POST", headers=_headers(),
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
        order_id = payload.get("orderId")
        return (True, order_id) if order_id else (False, f"No orderId: {payload}")
    except urllib.error.HTTPError as e:
        try:
            body_text = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            body_text = ""
        return False, f"HTTP {e.code}: {body_text}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# EMA(5) exit check - identical rule to your existing check_exit()
# ---------------------------------------------------------------------------

def calculate_ema(values, period=5):
    n = len(values)
    if n < period:
        return [None] * n
    k = 2 / (period + 1)
    ema = [None] * (period - 1)
    seed = sum(values[:period]) / period
    ema.append(seed)
    for price in values[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def check_exit(direction, candles):
    if len(candles) < 7:
        return False, None
    opens = [c[0] for c in candles]
    highs = [c[1] for c in candles]
    lows = [c[2] for c in candles]
    closes = [c[3] for c in candles]
    line = calculate_ema(lows if direction == "Buy" else highs, 5)
    for i in (-1, -2):
        if line[i] is None:
            return False, None
        if direction == "Buy":
            if not (closes[i] < opens[i] and closes[i] < line[i]):
                return False, None
        else:
            if not (closes[i] > opens[i] and closes[i] > line[i]):
                return False, None
    return True, closes[-1]


def debug_instruments():
    """Call this once after your first deploy and print/log the result to
    confirm the CSV column names above match reality."""
    equity_map, option_chains = load_instrument_master()
    return {
        "equity_matched": len(equity_map),
        "underlyings_with_options": len(option_chains),
        "reliance_resolved": "RELIANCE" in option_chains,
        "sample_underlyings": list(option_chains.keys())[:5],
    }
