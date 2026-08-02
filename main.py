from __future__ import annotations

import csv
import gzip
import io
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras

from flask import Flask, jsonify, render_template, request, redirect, url_for, make_response

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("DATABASE_URL", "")
IST_OFFSET = timedelta(hours=5, minutes=30)

app = Flask(__name__)

SECTOR_MAP = {
    "360ONE": "Financials",
    "ABB": "Industrials",
    "ABCAPITAL": "Financials",
    "ADANIENSOL": "Power & Utilities",
    "ADANIENT": "Services",
    "ADANIGREEN": "Power & Utilities",
    "ADANIPORTS": "Transportation",
    "ADANIPOWER": "Power & Utilities",
    "ALKEM": "Healthcare",
    "AMBER": "Consumer Discretionary",
    "AMBUJACEM": "Building Materials",
    "ANGELONE": "Financials",
    "APLAPOLLO": "Industrials",
    "APOLLOHOSP": "Healthcare",
    "ASHOKLEY": "Auto",
    "ASIANPAINT": "Building Materials",
    "ASTRAL": "Plastic Products",
    "AUBANK": "Bank",
    "AUROPHARMA": "Healthcare",
    "AXISBANK": "Bank",
    "BAJAJ-AUTO": "Auto",
    "BAJAJFINSV": "Financials",
    "BAJAJHLDNG": "Financials",
    "BAJFINANCE": "Financials",
    "BANDHANBNK": "Bank",
    "BANKBARODA": "Bank",
    "BANKINDIA": "Bank",
    "BANKNIFTY": "Indices",
    "BDL": "Aerospace & Defence",
    "BEL": "Aerospace & Defence",
    "BHARATFORG": "Industrials",
    "BHARTIARTL": "Telecom-Service",
    "BHEL": "Industrials",
    "BIOCON": "Healthcare",
    "BLUESTARCO": "Consumer Discretionary",
    "BOSCHLTD": "Auto",
    "BPCL": "Energy",
    "BRITANNIA": "Fmcg",
    "BSE": "Financials",
    "CAMS": "Financials",
    "CANBK": "Bank",
    "CDSL": "Financials",
    "CGPOWER": "Industrials",
    "CHOLAFIN": "Financials",
    "CIPLA": "Healthcare",
    "CNXMIDCAP": "Indices",
    "COALINDIA": "Metals & Mining",
    "COCHINSHIP": "Aerospace & Defence",
    "COFORGE": "I.T",
    "COLPAL": "Fmcg",
    "CONCOR": "Transportation",
    "CROMPTON": "Consumer Discretionary",
    "CUMMINSIND": "Industrials",
    "DABUR": "Fmcg",
    "DALBHARAT": "Building Materials",
    "DELHIVERY": "Transportation",
    "DIVISLAB": "Healthcare",
    "DIXON": "Consumer Discretionary",
    "DLF": "Realty",
    "DMART": "Consumer Discretionary",
    "DRREDDY": "Healthcare",
    "EICHERMOT": "Auto",
    "ETERNAL": "I.T",
    "EXIDEIND": "Auto",
    "FEDERALBNK": "Bank",
    "FORCEMOT": "Auto",
    "FORTIS": "Healthcare",
    "GAIL": "Energy",
    "GLENMARK": "Healthcare",
    "GMRAIRPORT": "Miscellaneous",
    "GODFRYPHLP": "Fmcg",
    "GODREJCP": "Fmcg",
    "GODREJPROP": "Realty",
    "GRASIM": "Textiles",
    "GVT&D": "Industrials",
    "HAL": "Aerospace & Defence",
    "HAVELLS": "Consumer Discretionary",
    "HCLTECH": "I.T",
    "HDFCAMC": "Financials",
    "HDFCBANK": "Bank",
    "HDFCLIFE": "Financials",
    "HEROMOTOCO": "Auto",
    "HINDALCO": "Metals & Mining",
    "HINDPETRO": "Energy",
    "HINDUNILVR": "Fmcg",
    "HINDZINC": "Metals & Mining",
    "HYUNDAI": "Auto",
    "ICICIBANK": "Bank",
    "ICICIGI": "Financials",
    "ICICIPRULI": "Financials",
    "IDEA": "Telecom-Service",
    "IDFCFIRSTB": "Bank",
    "IEX": "Financials",
    "INDHOTEL": "Services",
    "INDIANB": "Bank",
    "INDIGO": "Transportation",
    "INDUSINDBK": "Bank",
    "INDUSTOWER": "Telecom",
    "INFY": "I.T",
    "INOXWIND": "Industrials",
    "IOC": "Energy",
    "IREDA": "Financials",
    "IRFC": "Financials",
    "ITC": "Fmcg",
    "JINDALSTEL": "Metals & Mining",
    "JIOFIN": "Financials",
    "JSWENERGY": "Power & Utilities",
    "JSWSTEEL": "Metals & Mining",
    "JUBLFOOD": "Consumer Discretionary",
    "KALYANKJIL": "Consumer Discretionary",
    "KAYNES": "Consumer Discretionary",
    "KEI": "Industrials",
    "KFINTECH": "Financials",
    "KOTAKBANK": "Bank",
    "KPITTECH": "I.T",
    "LAURUSLABS": "Healthcare",
    "LICHSGFIN": "Financials",
    "LICI": "Financials",
    "LODHA": "Realty",
    "LT": "Realty",
    "LTF": "Financials",
    "LTM": "I.T",
    "LUPIN": "Healthcare",
    "M&M": "Auto",
    "MANAPPURAM": "Financials",
    "MANKIND": "Healthcare",
    "MARICO": "Fmcg",
    "MARUTI": "Auto",
    "MAXHEALTH": "Healthcare",
    "MAZDOCK": "Aerospace & Defence",
    "MCX": "Financials",
    "MFSL": "Miscellaneous",
    "MOTHERSON": "Auto",
    "MOTILALOFS": "Financials",
    "MPHASIS": "I.T",
    "MUTHOOTFIN": "Financials",
    "NAM-INDIA": "Financials",
    "NATIONALUM": "Metals & Mining",
    "NAUKRI": "I.T",
    "NBCC": "Miscellaneous",
    "NESTLEIND": "Fmcg",
    "NHPC": "Power & Utilities",
    "NIFTY": "Indices",
    "NMDC": "Metals & Mining",
    "NTPC": "Power & Utilities",
    "NUVAMA": "Financials",
    "NYKAA": "I.T",
    "OBEROIRLTY": "Realty",
    "OFSS": "I.T",
    "OIL": "Energy",
    "ONGC": "Energy",
    "PAGEIND": "Consumer Discretionary",
    "PATANJALI": "Fmcg",
    "PAYTM": "I.T",
    "PERSISTENT": "I.T",
    "PETRONET": "Energy",
    "PFC": "Financials",
    "PGEL": "Consumer Discretionary",
    "PHOENIXLTD": "Realty",
    "PIDILITIND": "Chemicals",
    "PIIND": "Chemicals",
    "PNB": "Bank",
    "PNBHOUSING": "Financials",
    "POLICYBZR": "I.T",
    "POLYCAB": "Industrials",
    "POWERGRID": "Power & Utilities",
    "POWERINDIA": "Industrials",
    "PREMIERENE": "Services",
    "PRESTIGE": "Realty",
    "RADICO": "Fmcg",
    "RBLBANK": "Bank",
    "RECLTD": "Financials",
    "RELIANCE": "Energy",
    "RVNL": "Realty",
    "SAIL": "Metals & Mining",
    "SBICARD": "Financials",
    "SBILIFE": "Financials",
    "SBIN": "Bank",
    "SHREECEM": "Building Materials",
    "SHRIRAMFIN": "Financials",
    "SIEMENS": "Industrials",
    "SOLARINDS": "Aerospace & Defence",
    "SONACOMS": "Auto",
    "SRF": "Chemicals",
    "SUNPHARMA": "Healthcare",
    "SUPREMEIND": "Plastic Products",
    "SUZLON": "Industrials",
    "SWIGGY": "I.T",
    "TATACONSUM": "Fmcg",
    "TATAELXSI": "I.T",
    "TATAPOWER": "Power & Utilities",
    "TATASTEEL": "Metals & Mining",
    "TCS": "I.T",
    "TECHM": "I.T",
    "TIINDIA": "Industrials",
    "TITAN": "Consumer Discretionary",
    "TMPV": "Auto",
    "TORNTPHARM": "Healthcare",
    "TRENT": "Consumer Discretionary",
    "TVSMOTOR": "Auto",
    "ULTRACEMCO": "Building Materials",
    "UNIONBANK": "Bank",
    "UNITDSPR": "Fmcg",
    "UNOMINDA": "Auto",
    "UPL": "Chemicals",
    "VBL": "Fmcg",
    "VEDL": "Metals & Mining",
    "VMM": "Consumer Discretionary",
    "VOLTAS": "Consumer Discretionary",
    "WAAREEENER": "Industrials",
    "WIPRO": "I.T",
    "YESBANK": "Bank",
    "ZYDUSLIFE": "Healthcare",
}


def get_sector(symbol: str) -> str:
    """Look up the sector for a stock symbol from the F&O watchlist mapping.
    Any symbol not in the list (new listings, non-F&O stocks, test data)
    falls back to 'Unclassified' rather than breaking the page."""
    return SECTOR_MAP.get((symbol or "").strip().upper(), "Unclassified")


ALL_SECTOR_NAMES = sorted(set(SECTOR_MAP.values()))


def ist_date_str(created_at_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(created_at_iso)
    except (ValueError, TypeError):
        return ""
    return (dt + IST_OFFSET).strftime("%Y-%m-%d")


def categorize(alert: dict) -> str:
    text = f"{alert.get('scan_name', '')} {alert.get('alert_name', '')}".lower()
    if "sell" in text:
        return "Sell"
    if "buy" in text:
        return "Buy"
    return "Others"


CATEGORY_ORDER = ["Sell", "Buy", "Others"]


def merge_duplicate_symbols(items: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for a in items:
        groups.setdefault(a.get("symbol", ""), []).append(a)

    merged = []
    for symbol, group in groups.items():
        seen_scans = set()
        scan_names = []
        alert_name = ""
        for a in group:
            sn = a.get("scan_name", "")
            if sn not in seen_scans:
                seen_scans.add(sn)
                scan_names.append(sn)
            if not alert_name and a.get("alert_name"):
                alert_name = a["alert_name"]

        newest = group[0]
        combined = dict(newest)
        combined["alert_name"] = alert_name
        combined["scan_names"] = scan_names
        combined["confirmed_count"] = len(scan_names)
        merged.append(combined)
    return merged


def group_by_category(alerts: list[dict]) -> list[tuple[str, list[dict]]]:
    buckets = {name: [] for name in CATEGORY_ORDER}
    for alert in alerts:
        buckets[categorize(alert)].append(alert)
    result = []
    for name in CATEGORY_ORDER:
        if buckets[name]:
            result.append((name, merge_duplicate_symbols(buckets[name])))
    return result


class PGConnWrapper:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        pg_query = query.replace("?", "%s")
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(pg_query, params or ())
        return cur

    def commit(self):
        self._conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._conn.close()
        return False


def get_db():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set - add your Neon "
            "connection string in Render's Environment settings."
        )
    conn = psycopg2.connect(DATABASE_URL)
    return PGConnWrapper(conn)


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                batch_id TEXT,
                symbol TEXT,
                trigger_price TEXT,
                scan_name TEXT,
                scan_url TEXT,
                alert_name TEXT,
                triggered_at TEXT,
                raw_payload TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_trades (
                id SERIAL PRIMARY KEY,
                symbol TEXT,
                direction TEXT,
                entry_price DOUBLE PRECISION,
                entry_time TEXT,
                status TEXT DEFAULT 'OPEN',
                exit_price DOUBLE PRECISION,
                exit_time TEXT,
                pnl DOUBLE PRECISION,
                exit_reason TEXT,
                last_checked_price DOUBLE PRECISION,
                last_checked_time TEXT,
                last_error TEXT,
                quantity INTEGER DEFAULT 0,
                pnl_pct DOUBLE PRECISION,
                live_status TEXT DEFAULT 'NONE',
                live_entry_order_id TEXT,
                live_exit_order_id TEXT,
                live_error TEXT,
                live_quantity INTEGER,
                live_instrument_key TEXT,
                live_option_label TEXT,
                paper_instrument_key TEXT,
                paper_option_label TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sector_prev_close (
                symbol TEXT PRIMARY KEY,
                close DOUBLE PRECISION,
                date TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS live_order_queue (
                id SERIAL PRIMARY KEY,
                trade_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                symbol TEXT,
                direction TEXT,
                reference_price TEXT,
                security_id TEXT,
                quantity INTEGER,
                status TEXT NOT NULL DEFAULT 'PENDING',
                result_order_id TEXT,
                result_error TEXT,
                created_at TEXT NOT NULL,
                processed_at TEXT
            )
            """
        )
        for stmt in (
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS live_status TEXT DEFAULT 'NONE'",
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS live_entry_order_id TEXT",
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS live_exit_order_id TEXT",
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS live_error TEXT",
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS live_quantity INTEGER",
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS live_instrument_key TEXT",
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS live_option_label TEXT",
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS paper_instrument_key TEXT",
            "ALTER TABLE paper_trades ADD COLUMN IF NOT EXISTS paper_option_label TEXT",
        ):
            conn.execute(stmt)
        conn.commit()


DEFAULT_CAPITAL = 100000.0


def get_capital() -> float:
    value = get_setting("paper_trade_capital", str(DEFAULT_CAPITAL))
    try:
        return float(value)
    except (ValueError, TypeError):
        return DEFAULT_CAPITAL


def get_live_trading_enabled() -> bool:
    return get_setting("live_trading_enabled", "false") == "true"


def get_setting(key: str, default: str | None = None) -> str | None:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


def save_alert_batch(data: dict):
    stocks = [s.strip() for s in str(data.get("stocks", "")).split(",") if s.strip()]
    prices = [p.strip() for p in str(data.get("trigger_prices", "")).split(",") if p.strip()]

    if not stocks:
        stocks = [data.get("symbol", "UNKNOWN")]
        prices = [str(data.get("price", ""))]

    batch_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    raw_payload = json.dumps(data, ensure_ascii=False)

    with get_db() as conn:
        for i, symbol in enumerate(stocks):
            price = prices[i] if i < len(prices) else ""
            conn.execute(
                """
                INSERT INTO alerts
                    (batch_id, symbol, trigger_price, scan_name, scan_url,
                     alert_name, triggered_at, raw_payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id, symbol, price, data.get("scan_name", ""),
                    data.get("scan_url", ""), data.get("alert_name", ""),
                    data.get("triggered_at", ""), raw_payload, created_at,
                ),
            )
        conn.commit()


def get_current_capital() -> float:
    base = get_capital()
    with get_db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(pnl), 0) AS total FROM paper_trades WHERE status = 'CLOSED'"
        ).fetchone()
    return base + (row["total"] or 0)


def _mark_live_failed(trade_id: int, error: str, live_quantity: int | None = None) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE paper_trades SET live_status = 'FAILED', live_error = ?, "
            "live_quantity = COALESCE(?, live_quantity) WHERE id = ?",
            (error, live_quantity, trade_id),
        )
        conn.commit()


def queue_live_place(trade_id: int, symbol: str, direction: str, reference_price: float) -> None:
    """Writes a PLACE row for the Dhan Cloud script to pick up on its next
    scheduled run, instead of calling Dhan's order API directly from here -
    this is what keeps Render's own outbound IP out of the picture
    entirely for live order placement."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO live_order_queue
                (trade_id, action, symbol, direction, reference_price, status, created_at)
            VALUES (?, 'PLACE', ?, ?, ?, 'PENDING', ?)
            """,
            (trade_id, symbol, direction, str(reference_price), now),
        )
        conn.execute(
            "UPDATE paper_trades SET live_status = 'PENDING' WHERE id = ?",
            (trade_id,),
        )
        conn.commit()


def queue_live_close(trade_id: int, security_id: str, quantity: int) -> None:
    """Writes a CLOSE row for the exact contract held (security_id, quantity
    from this trade's own live_instrument_key/live_quantity columns)."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO live_order_queue
                (trade_id, action, security_id, quantity, status, created_at)
            VALUES (?, 'CLOSE', ?, ?, 'PENDING', ?)
            """,
            (trade_id, security_id, quantity, now),
        )
        conn.commit()


def create_paper_trades_for_batch(data: dict) -> None:
    category = categorize(data)
    if category not in ("Buy", "Sell"):
        return

    with get_db() as conn:
        already_open = conn.execute(
            "SELECT id FROM paper_trades WHERE status = 'OPEN' LIMIT 1"
        ).fetchone()
    if already_open:
        return

    stocks = [s.strip() for s in str(data.get("stocks", "")).split(",") if s.strip()]
    prices = [p.strip() for p in str(data.get("trigger_prices", "")).split(",") if p.strip()]
    if not stocks:
        stocks = [data.get("symbol", "UNKNOWN")]
        prices = [str(data.get("price", ""))]

    symbol = None
    price_val = None
    for i, s in enumerate(stocks):
        p = prices[i] if i < len(prices) else ""
        try:
            candidate = float(p)
        except (ValueError, TypeError):
            continue
        if candidate > 0:
            symbol, price_val = s, candidate
            break
    if symbol is None:
        return

    opt_type = "CE" if category == "Buy" else "PE"
    access_token = get_setting("dhan_access_token")
    option = get_atm_option(symbol, opt_type, price_val) if access_token else None
    premium = get_ltp(option["instrument_key"], access_token) if option else None

    paper_instrument_key = None
    paper_option_label = None
    fallback_note = None
    if option and premium and premium > 0:
        capital = get_current_capital()
        lot_size = option["lot_size"]
        lots = max(1, int(capital // (premium * lot_size)))
        quantity = lots * lot_size
        entry_price = premium
        paper_instrument_key = option["instrument_key"]
        paper_option_label = f"{symbol} {option['strike']:g} {opt_type} exp {option['expiry']}"
    else:
        capital = get_current_capital()
        quantity = int(capital // price_val) or 1
        entry_price = price_val
        if not access_token:
            fallback_note = "No Dhan token saved - fell back to equity paper trading"
        elif not option:
            fallback_note = f"No {opt_type} option chain data for {symbol} - fell back to equity paper trading"
        else:
            fallback_note = f"Could not fetch option premium for {symbol} {opt_type} - fell back to equity paper trading"

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute(
            """
            INSERT INTO paper_trades
                (symbol, direction, entry_price, entry_time, status, quantity,
                 paper_instrument_key, paper_option_label, last_error)
            VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)
            RETURNING id
            """,
            (symbol, category, entry_price, now, quantity, paper_instrument_key, paper_option_label, fallback_note),
        ).fetchone()
        conn.commit()

    if get_live_trading_enabled():
        trade_id = row["id"]
        if not access_token:
            _mark_live_failed(trade_id, "Live trading is on but no Dhan access token is saved")
        elif not option:
            _mark_live_failed(trade_id, f"No {opt_type} option chain data found for {symbol} (nearest monthly expiry)")
        elif not premium or premium <= 0:
            _mark_live_failed(trade_id, f"Could not fetch option premium for {symbol} {opt_type}")
        else:
            # No funds/quantity/order-placement call here anymore - the
            # Dhan Cloud script does that (funds check, quantity sizing,
            # and the actual order) on its next scheduled run, from Dhan's
            # own trusted infra. Render just queues the request.
            queue_live_place(trade_id, symbol, category, price_val)


def calculate_ema(values: list[float], period: int = 5) -> list[float | None]:
    n = len(values)
    if n < period:
        return [None] * n
    k = 2 / (period + 1)
    ema: list[float | None] = [None] * (period - 1)
    seed = sum(values[:period]) / period
    ema.append(seed)
    for price in values[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def check_exit(direction: str, candles: list[tuple[float, float, float, float]]):
    if len(candles) < 7:
        return False, None

    opens = [c[0] for c in candles]
    highs = [c[1] for c in candles]
    lows = [c[2] for c in candles]
    closes = [c[3] for c in candles]

    if direction == "Buy":
        ema_line = calculate_ema(lows, 5)
        for i in (-1, -2):
            if ema_line[i] is None:
                return False, None
            if not (closes[i] < opens[i] and closes[i] < ema_line[i]):
                return False, None
        return True, closes[-1]
    else:
        ema_line = calculate_ema(highs, 5)
        for i in (-1, -2):
            if ema_line[i] is None:
                return False, None
            if not (closes[i] > opens[i] and closes[i] > ema_line[i]):
                return False, None
        return True, closes[-1]


_instrument_cache: dict[str, str] = {}
_instrument_cache_date: str | None = None
_instrument_debug: dict = {}

_option_chain_cache: dict[str, list[dict]] = {}
_option_debug: dict = {}

DHAN_INSTRUMENTS_URL = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"


def _load_instrument_master() -> None:
    """Downloads Dhan's public detailed scrip master CSV once per IST day
    and builds two lookups: NSE-equity symbol -> securityId, and
    underlying -> list of option contracts (strike/expiry/opt_type/
    securityId/lot_size).

    NOTE: column names below were confirmed directly against a live
    /api/paper-trading/debug-instruments response on 2026-08-02 - Dhan's
    file does NOT use a "SEM_" prefix (only SM_EXPIRY_DATE keeps a short
    prefix). Real header list: EXCH_ID, SEGMENT, SECURITY_ID, ISIN,
    INSTRUMENT, UNDERLYING_SECURITY_ID, UNDERLYING_SYMBOL, SYMBOL_NAME,
    DISPLAY_NAME, INSTRUMENT_TYPE, SERIES, LOT_SIZE, SM_EXPIRY_DATE,
    STRIKE_PRICE, OPTION_TYPE, TICK_SIZE, ... If matched_count or
    option_rows_matched still come back 0 after this fix, re-check
    /api/paper-trading/debug-instruments's sample_rows for an actual
    equity row (the earlier debug output only showed BSE currency
    futures samples, not a confirmed NSE equity row)."""
    global _instrument_cache, _instrument_cache_date, _instrument_debug
    global _option_chain_cache, _option_debug
    try:
        req = urllib.request.Request(DHAN_INSTRUMENTS_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_bytes = resp.read()
        text = raw_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []

        mapping = {}
        option_chains: dict[str, list[dict]] = {}
        sample_rows = []
        fo_sample_rows = []
        equity_sample_rows = []
        row_count = 0
        option_row_count = 0

        for i, row in enumerate(reader):
            row_count = i + 1
            if i < 3:
                sample_rows.append(dict(row))
            exch = (row.get("EXCH_ID") or "").upper()
            instr = (row.get("INSTRUMENT") or "").upper()
            sec_id = row.get("SECURITY_ID")
            tsym = (row.get("SYMBOL_NAME") or "").upper()

            if exch == "NSE" and instr == "EQUITY" and tsym and sec_id:
                mapping[tsym] = sec_id
                if len(equity_sample_rows) < 3:
                    equity_sample_rows.append(dict(row))
            elif instr in ("OPTSTK", "OPTIDX") and sec_id:
                if len(fo_sample_rows) < 3:
                    fo_sample_rows.append(dict(row))
                opt_type = (row.get("OPTION_TYPE") or "").upper()
                if opt_type not in ("CE", "PE"):
                    continue
                underlying = (row.get("UNDERLYING_SYMBOL") or "").upper()
                try:
                    strike = float(row.get("STRIKE_PRICE") or 0) or None
                except (TypeError, ValueError):
                    strike = None
                try:
                    lot_size = int(float(row.get("LOT_SIZE") or 0)) or None
                except (TypeError, ValueError):
                    lot_size = None
                expiry = (row.get("SM_EXPIRY_DATE") or "")[:10] or None

                if underlying and strike and expiry and lot_size and sec_id:
                    option_row_count += 1
                    option_chains.setdefault(underlying, []).append({
                        "strike": strike,
                        "opt_type": opt_type,
                        "expiry": expiry,
                        "instrument_key": sec_id,
                        "lot_size": lot_size,
                    })

        _instrument_cache = mapping
        _option_chain_cache = option_chains
        _instrument_cache_date = (datetime.utcnow() + IST_OFFSET).strftime("%Y-%m-%d")
        _instrument_debug = {
            "ok": True,
            "raw_bytes_len": len(raw_bytes),
            "fieldnames": fieldnames,
            "sample_rows": sample_rows,
            "equity_sample_rows": equity_sample_rows,
            "total_rows_scanned": row_count,
            "matched_count": len(mapping),
            "error": None,
        }
        _option_debug = {
            "ok": True,
            "fo_sample_rows": fo_sample_rows,
            "option_rows_matched": option_row_count,
            "underlyings_with_options": len(option_chains),
            "sample_underlyings": list(option_chains.keys())[:5],
            "reliance_resolved": "RELIANCE" in option_chains,
        }
    except Exception as e:
        import traceback
        _instrument_cache = {}
        _option_chain_cache = {}
        _instrument_debug = {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
        _option_debug = {"ok": False, "error": str(e)}


def get_instrument_key(symbol: str) -> str | None:
    today = (datetime.utcnow() + IST_OFFSET).strftime("%Y-%m-%d")
    if _instrument_cache_date != today or not _instrument_cache:
        _load_instrument_master()
    return _instrument_cache.get((symbol or "").upper())


def get_atm_option(symbol: str, opt_type: str, reference_price: float) -> dict | None:
    today = (datetime.utcnow() + IST_OFFSET).strftime("%Y-%m-%d")
    if _instrument_cache_date != today or not _option_chain_cache:
        _load_instrument_master()
    contracts = _option_chain_cache.get((symbol or "").upper())
    if not contracts:
        return None

    all_expiries = sorted({c["expiry"] for c in contracts if c["expiry"] >= today})
    if not all_expiries:
        return None
    monthly_by_month: dict[str, str] = {}
    for exp in all_expiries:
        month_key = exp[:7]
        if month_key not in monthly_by_month or exp > monthly_by_month[month_key]:
            monthly_by_month[month_key] = exp
    nearest_monthly = min(monthly_by_month.values())

    candidates = [c for c in contracts if c["expiry"] == nearest_monthly and c["opt_type"] == opt_type]
    if not candidates:
        return None
    return min(candidates, key=lambda c: abs(c["strike"] - reference_price))


_sector_perf_cache: dict = {"data": None, "fetched_at": None}
_sector_perf_debug: dict = {"ok": None, "error": None}
SECTOR_PERF_CACHE_SECONDS = 5

_prev_close_cache: dict = {"date": None, "closes": {}}
_prev_close_loading = False


def _ist_today_str() -> str:
    return (datetime.utcnow() + IST_OFFSET).strftime("%Y-%m-%d")


def _load_prev_closes_background(access_token: str) -> None:
    """Runs in a background thread: loops every mapped symbol and fetches
    its most recent completed daily candle's close via Dhan's historical
    daily-candle endpoint. Each symbol's close is written to the DB as
    soon as it's fetched, same resilience pattern as before."""
    global _prev_close_cache, _prev_close_loading
    today = _ist_today_str()
    from_date = (datetime.utcnow() + IST_OFFSET - timedelta(days=10)).strftime("%Y-%m-%d")
    closes: dict[str, float] = dict(_prev_close_cache["closes"])
    for symbol in SECTOR_MAP:
        if symbol in closes:
            continue
        key = get_instrument_key(symbol)
        if not key:
            continue
        body = {
            "securityId": str(key),
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "fromDate": from_date,
            "toDate": today,
        }
        req = urllib.request.Request(
            "https://api.dhan.co/v2/charts/historical",
            data=json.dumps(body).encode(), method="POST",
            headers={"access-token": access_token, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode())
            closes_list = payload.get("close") or []
            if closes_list:
                # last COMPLETED day - if today's still-open session is
                # included as the last element, this may need adjusting
                # once confirmed against a live response.
                close = closes_list[-2] if len(closes_list) > 1 else closes_list[-1]
                closes[symbol] = close
                _prev_close_cache = {"date": today, "closes": dict(closes)}
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO sector_prev_close (symbol, close, date) VALUES (?, ?, ?) "
                        "ON CONFLICT(symbol) DO UPDATE SET close = excluded.close, date = excluded.date",
                        (symbol, close, today),
                    )
                    conn.commit()
        except Exception:
            continue
    _prev_close_cache = {"date": today, "closes": closes}
    _prev_close_loading = False


def _load_prev_closes_from_db() -> dict[str, float]:
    today = _ist_today_str()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT symbol, close FROM sector_prev_close WHERE date = ?", (today,)
        ).fetchall()
    return {row["symbol"]: row["close"] for row in rows}


def _get_prev_closes(access_token: str) -> dict[str, float]:
    global _prev_close_loading, _prev_close_cache
    today = _ist_today_str()
    if _prev_close_cache["date"] != today:
        _prev_close_cache = {"date": today, "closes": _load_prev_closes_from_db()}
    if len(_prev_close_cache["closes"]) < len(SECTOR_MAP) and not _prev_close_loading:
        _prev_close_loading = True
        threading.Thread(target=_load_prev_closes_background, args=(access_token,), daemon=True).start()
    return _prev_close_cache["closes"]


def _fetch_sector_performance(access_token: str) -> dict | None:
    """Computes each sector's today's % change as the average % change of
    its own constituent stocks. Uses Dhan's marketfeed/ltp endpoint,
    batched by exchange segment (NSE_EQ), instead of Upstox's LTP call."""
    global _sector_perf_debug
    prev_closes = _get_prev_closes(access_token)
    if not prev_closes:
        _sector_perf_debug = {"ok": False, "error": "Previous closes still loading in the background - try again shortly"}
        return None

    symbol_to_sector = SECTOR_MAP
    instrument_key_to_symbol: dict[str, str] = {}
    for symbol in prev_closes:
        key = get_instrument_key(symbol)
        if key:
            instrument_key_to_symbol[str(key)] = symbol
    if not instrument_key_to_symbol:
        _sector_perf_debug = {"ok": False, "error": "No instrument keys resolved for symbols with a cached previous close"}
        return None

    security_ids = [int(k) for k in instrument_key_to_symbol.keys()]
    body = {"NSE_EQ": security_ids}
    req = urllib.request.Request(
        "https://api.dhan.co/v2/marketfeed/ltp",
        data=json.dumps(body).encode(), method="POST",
        headers={"access-token": access_token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body_text = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            body_text = ""
        _sector_perf_debug = {"ok": False, "error": f"HTTP {e.code}: {body_text}"}
        return None
    except Exception as e:
        _sector_perf_debug = {"ok": False, "error": str(e)}
        return None

    data = (payload.get("data") or {}).get("NSE_EQ") or {}
    sector_changes: dict[str, list[float]] = {}
    unmatched_tokens = []
    for sec_id_str, entry in data.items():
        symbol = instrument_key_to_symbol.get(str(sec_id_str))
        if not symbol:
            if len(unmatched_tokens) < 3:
                unmatched_tokens.append(sec_id_str)
            continue
        last_price = entry.get("last_price")
        prev_close = prev_closes.get(symbol)
        if not last_price or not prev_close:
            continue
        pct = (last_price - prev_close) / prev_close * 100
        sector = symbol_to_sector.get(symbol, "Unclassified")
        sector_changes.setdefault(sector, []).append(pct)

    result = {
        sector: {"pct_change": round(sum(vals) / len(vals), 2), "count": len(vals)}
        for sector, vals in sector_changes.items()
    }
    _sector_perf_debug = {
        "ok": True,
        "error": None,
        "prev_closes_cached": len(prev_closes),
        "instrument_keys_sent": len(security_ids),
        "data_entries_received": len(data),
        "unmatched_instrument_tokens_sample": unmatched_tokens,
        "sectors_matched": len(result),
    }
    return result


def get_sector_performance_cached(access_token: str | None) -> dict | None:
    global _sector_perf_cache
    if not access_token:
        return None
    now = datetime.utcnow()
    fetched_at = _sector_perf_cache["fetched_at"]
    if fetched_at and (now - fetched_at).total_seconds() < SECTOR_PERF_CACHE_SECONDS:
        return _sector_perf_cache["data"]
    value = _fetch_sector_performance(access_token)
    _sector_perf_cache = {"data": value, "fetched_at": now}
    return value


def fetch_5min_candles(instrument_key: str, access_token: str) -> list[tuple[float, float, float, float]]:
    """Dhan supports interval=5 natively - no resampling step needed here
    (unlike Upstox's 1min-only intraday API)."""
    now_ist = datetime.utcnow() + IST_OFFSET
    from_dt = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    body = {
        "securityId": str(instrument_key),
        "exchangeSegment": "NSE_FNO",
        "instrument": "OPTSTK",
        "interval": 5,
        "oi": False,
        "fromDate": from_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
    }
    req = urllib.request.Request(
        "https://api.dhan.co/v2/charts/intraday",
        data=json.dumps(body).encode(), method="POST",
        headers={"access-token": access_token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())
    return list(zip(payload.get("open", []), payload.get("high", []),
                     payload.get("low", []), payload.get("close", [])))


_funds_debug: dict = {"ok": None, "error": None, "raw": None}


def get_dhan_available_funds(access_token: str) -> float | None:
    global _funds_debug
    req = urllib.request.Request(
        "https://api.dhan.co/v2/fundlimit",
        headers={"access-token": access_token, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
        total = payload.get("availabelBalance", payload.get("availableBalance"))
        if total is None:
            _funds_debug = {"ok": False, "error": f"No balance field in response: {payload}", "raw": payload}
            return None
        _funds_debug = {"ok": True, "error": None, "raw": payload}
        return float(total)
    except urllib.error.HTTPError as e:
        try:
            body_text = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            body_text = ""
        _funds_debug = {"ok": False, "error": f"HTTP {e.code}: {body_text}", "raw": None}
        return None
    except Exception as e:
        _funds_debug = {"ok": False, "error": str(e), "raw": None}
        return None


_funds_display_cache: dict = {"value": None, "fetched_at": None}
FUNDS_DISPLAY_CACHE_SECONDS = 20


def get_dhan_available_funds_for_display(access_token: str) -> float | None:
    global _funds_display_cache
    now = datetime.utcnow()
    fetched_at = _funds_display_cache["fetched_at"]
    if fetched_at and (now - fetched_at).total_seconds() < FUNDS_DISPLAY_CACHE_SECONDS:
        return _funds_display_cache["value"]
    value = get_dhan_available_funds(access_token)
    _funds_display_cache = {"value": value, "fetched_at": now}
    return value


def get_ltp(instrument_key: str, access_token: str) -> float | None:
    body = {"NSE_FNO": [int(instrument_key)]}
    req = urllib.request.Request(
        "https://api.dhan.co/v2/marketfeed/ltp",
        data=json.dumps(body).encode(), method="POST",
        headers={"access-token": access_token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
        entry = (payload.get("data") or {}).get("NSE_FNO", {}).get(str(instrument_key)) or {}
        return entry.get("last_price")
    except Exception:
        return None


def compute_live_stats(open_trades: list[dict], closed_trades: list[dict]) -> dict:
    live_open = sum(1 for t in open_trades if t.get("live_status") == "OPEN")
    live_closed_trades = [t for t in closed_trades if t.get("live_status") == "CLOSED"]
    live_pnl = 0.0
    for t in live_closed_trades:
        qty = t.get("live_quantity") or 0
        entry = t.get("entry_price") or 0
        exit_p = t.get("exit_price") or 0
        live_pnl += (exit_p - entry) * qty
    return {
        "live_open": live_open,
        "live_closed": len(live_closed_trades),
        "live_pnl": round(live_pnl, 2),
    }


def _close_live_position_if_any(trade: dict, access_token: str | None) -> tuple[str | None, str | None]:
    """If this paper trade has a live position open, queues a CLOSE row
    for the Dhan Cloud script instead of calling Dhan's order API
    directly. Returns (None, None) always now, since the actual order_id
    comes back later when the Dhan Cloud script processes the row and
    updates paper_trades itself - the caller here no longer gets an
    immediate result."""
    if trade.get("live_status") != "OPEN":
        return None, None

    instrument_key = trade.get("live_instrument_key")
    if not instrument_key:
        return None, "No live_instrument_key recorded on this trade - could not queue live close"

    qty = trade.get("live_quantity") or 1
    queue_live_close(trade["id"], instrument_key, qty)
    return None, None


def run_paper_trade_check() -> dict:
    access_token = get_setting("dhan_access_token")
    if not access_token:
        return {"checked": 0, "closed": 0, "error": "No Dhan access token saved yet."}

    with get_db() as conn:
        open_trades = conn.execute(
            "SELECT * FROM paper_trades WHERE status = 'OPEN'"
        ).fetchall()

    checked = 0
    closed = 0
    errors = []
    now = datetime.utcnow().isoformat()

    for trade in open_trades:
        checked += 1
        symbol = trade["symbol"]
        try:
            instrument_key = trade["paper_instrument_key"] or get_instrument_key(symbol)
            if not instrument_key:
                with get_db() as conn:
                    conn.execute(
                        "UPDATE paper_trades SET last_error = ?, last_checked_time = ? WHERE id = ?",
                        (f"No instrument_key found for {symbol}", now, trade["id"]),
                    )
                    conn.commit()
                continue

            candles = fetch_5min_candles(instrument_key, access_token)
            exited, exit_price = check_exit(trade["direction"], candles)
            last_price = candles[-1][3] if candles else None

            if exited:
                live_exit_order_id, live_exit_error = _close_live_position_if_any(trade, access_token)

            with get_db() as conn:
                if exited:
                    entry_price = trade["entry_price"]
                    qty = trade["quantity"] or 1
                    if trade["direction"] == "Buy":
                        pnl = (exit_price - entry_price) * qty
                    else:
                        pnl = (entry_price - exit_price) * qty
                    pnl = round(pnl, 2)
                    capital_used = entry_price * qty
                    pnl_pct = round((pnl / capital_used) * 100, 2) if capital_used else 0
                    conn.execute(
                        """
                        UPDATE paper_trades
                        SET status = 'CLOSED', exit_price = ?, exit_time = ?,
                            pnl = ?, pnl_pct = ?, exit_reason = ?, last_checked_price = ?,
                            last_checked_time = ?, last_error = NULL,
                            live_status = CASE WHEN live_status = 'OPEN' THEN 'CLOSING' ELSE live_status END
                        WHERE id = ?
                        """,
                        (
                            exit_price, now, pnl, pnl_pct, "5-EMA exit rule", last_price, now,
                            trade["id"],
                        ),
                    )
                    closed += 1
                else:
                    conn.execute(
                        "UPDATE paper_trades SET last_checked_price = ?, last_checked_time = ?, last_error = NULL WHERE id = ?",
                        (last_price, now, trade["id"]),
                    )
                conn.commit()
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                body = ""
            msg = f"Dhan API error {e.code} for {symbol}: {body}"
            errors.append(msg)
            with get_db() as conn:
                conn.execute(
                    "UPDATE paper_trades SET last_error = ?, last_checked_time = ? WHERE id = ?",
                    (msg, now, trade["id"]),
                )
                conn.commit()
        except Exception as e:
            msg = f"{symbol}: {e}"
            errors.append(msg)
            with get_db() as conn:
                conn.execute(
                    "UPDATE paper_trades SET last_error = ?, last_checked_time = ? WHERE id = ?",
                    (msg, now, trade["id"]),
                )
                conn.commit()

    return {"checked": checked, "closed": closed, "errors": errors}


@app.route("/api/sectors")
def api_sectors():
    access_token = get_setting("dhan_access_token")
    perf = get_sector_performance_cached(access_token)
    result = [
        {
            "sector": sector,
            "pct_change": (perf or {}).get(sector, {}).get("pct_change"),
        }
        for sector in ALL_SECTOR_NAMES
    ]
    return jsonify(result)


@app.route("/api/paper-trading/debug-sector-perf")
def debug_sector_perf():
    access_token = get_setting("dhan_access_token")
    if not access_token:
        return jsonify({"ok": False, "error": "No Dhan access token saved"})
    global _sector_perf_cache
    _sector_perf_cache = {"data": None, "fetched_at": None}
    value = get_sector_performance_cached(access_token)
    return jsonify({
        "value": value,
        "prev_close_cache_date": _prev_close_cache["date"],
        "prev_closes_loaded": len(_prev_close_cache["closes"]),
        "prev_close_still_loading": _prev_close_loading,
        **_sector_perf_debug,
    })


@app.route("/")
def index():
    try:
        selected_date = request.args.get("date", "")
        today_str = (datetime.utcnow() + IST_OFFSET).strftime("%Y-%m-%d")
        if not selected_date:
            selected_date = today_str

        with get_db() as conn:
            all_alerts = conn.execute(
                "SELECT * FROM alerts ORDER BY id DESC LIMIT 2000"
            ).fetchall()

        available_dates = sorted(
            {ist_date_str(a["created_at"]) for a in all_alerts if a["created_at"]},
            reverse=True,
        )
        if selected_date not in available_dates and available_dates:
            selected_date = available_dates[0]

        alerts = [
            dict(a) for a in all_alerts if ist_date_str(a["created_at"]) == selected_date
        ]
        for a in alerts:
            a["category"] = categorize(a)
            a["sector"] = get_sector(a.get("symbol", ""))
        all_sectors = sorted({a["sector"] for a in alerts})
        grouped = group_by_category(alerts)
        merged_count = sum(len(items) for _, items in grouped)

        html = render_template(
            "index.html",
            alerts_count=merged_count,
            grouped=grouped,
            all_sectors=all_sectors,
            all_sector_names=ALL_SECTOR_NAMES,
            available_dates=available_dates,
            selected_date=selected_date,
            today_str=today_str,
        )
    except Exception:
        import traceback
        return f"<pre>{traceback.format_exc()}</pre>", 500

    body = html.encode("utf-8")
    response = make_response(body)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Length"] = str(len(body))
    return response


@app.route("/api/alerts")
def api_alerts():
    selected_date = request.args.get("date", "")
    today_str = (datetime.utcnow() + IST_OFFSET).strftime("%Y-%m-%d")
    if not selected_date:
        selected_date = today_str

    with get_db() as conn:
        all_alerts = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT 2000"
        ).fetchall()

    alerts = [
        dict(a) for a in all_alerts if ist_date_str(a["created_at"]) == selected_date
    ]
    for a in alerts:
        a["category"] = categorize(a)
        a["sector"] = get_sector(a.get("symbol", ""))

    by_category: dict[str, list[dict]] = {}
    for a in alerts:
        by_category.setdefault(a["category"], []).append(a)

    merged_alerts: list[dict] = []
    for name in CATEGORY_ORDER:
        if name in by_category:
            merged_alerts.extend(merge_duplicate_symbols(by_category[name]))

    return jsonify(merged_alerts)


@app.route("/webhook/chartink", methods=["POST"])
def chartink_webhook():
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()

    save_alert_batch(data)
    create_paper_trades_for_batch(data)
    return jsonify({"status": "ok"}), 200


@app.route("/clear", methods=["POST"])
def clear_alerts():
    with get_db() as conn:
        conn.execute("DELETE FROM alerts")
        conn.commit()
    return redirect(url_for("index"))


def attach_unrealized_pnl(open_trades: list[dict]) -> None:
    for t in open_trades:
        last_price = t.get("last_checked_price")
        qty = t.get("quantity") or 1
        entry = t["entry_price"]
        capital_used = entry * qty
        if last_price is None:
            t["unrealized_pnl"] = None
            t["unrealized_pnl_pct"] = None
            continue
        if t["direction"] == "Buy":
            pnl = (last_price - entry) * qty
        else:
            pnl = (entry - last_price) * qty
        t["unrealized_pnl"] = round(pnl, 2)
        t["unrealized_pnl_pct"] = round((pnl / capital_used) * 100, 2) if capital_used else 0


def attach_running_balance(closed_trades_desc: list[dict], starting_capital: float) -> None:
    running = starting_capital
    for t in reversed(closed_trades_desc):
        running += t["pnl"] or 0
        t["balance_after"] = round(running, 2)


@app.route("/paper-trading")
def paper_trading():
    with get_db() as conn:
        open_trades = conn.execute(
            "SELECT * FROM paper_trades WHERE status = 'OPEN' ORDER BY id DESC"
        ).fetchall()
        closed_trades = conn.execute(
            "SELECT * FROM paper_trades WHERE status = 'CLOSED' ORDER BY id DESC LIMIT 200"
        ).fetchall()

    open_trades = [dict(t) for t in open_trades]
    closed_trades = [dict(t) for t in closed_trades]
    attach_unrealized_pnl(open_trades)

    total_pnl = sum(t["pnl"] for t in closed_trades if t["pnl"] is not None)
    wins = sum(1 for t in closed_trades if (t["pnl"] or 0) > 0)
    total_closed = len(closed_trades)
    win_rate = round((wins / total_closed) * 100, 1) if total_closed else 0

    token_saved = bool(get_setting("dhan_access_token"))
    capital = get_capital()
    attach_running_balance(closed_trades, capital)
    current_capital = get_current_capital()
    live_trading_enabled = get_live_trading_enabled()

    live_stats = compute_live_stats(open_trades, closed_trades)
    live_available_funds = None
    if token_saved:
        live_available_funds = get_dhan_available_funds_for_display(get_setting("dhan_access_token"))

    html = render_template(
        "paper_trading.html",
        open_trades=open_trades,
        closed_trades=closed_trades,
        total_pnl=round(total_pnl, 2),
        win_rate=win_rate,
        total_closed=total_closed,
        wins=wins,
        token_saved=token_saved,
        capital=capital,
        current_capital=round(current_capital, 2),
        live_trading_enabled=live_trading_enabled,
        live_open=live_stats["live_open"],
        live_closed=live_stats["live_closed"],
        live_pnl=live_stats["live_pnl"],
        live_available_funds=live_available_funds,
    )
    body = html.encode("utf-8")
    response = make_response(body)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Length"] = str(len(body))
    return response


@app.route("/api/paper-trading/data")
def paper_trading_data():
    with get_db() as conn:
        open_trades = conn.execute(
            "SELECT * FROM paper_trades WHERE status = 'OPEN' ORDER BY id DESC"
        ).fetchall()
        closed_trades = conn.execute(
            "SELECT * FROM paper_trades WHERE status = 'CLOSED' ORDER BY id DESC LIMIT 200"
        ).fetchall()
    open_trades = [dict(t) for t in open_trades]
    closed_trades = [dict(t) for t in closed_trades]
    attach_unrealized_pnl(open_trades)
    attach_running_balance(closed_trades, get_capital())

    live_stats = compute_live_stats(open_trades, closed_trades)
    access_token = get_setting("dhan_access_token")
    live_available_funds = get_dhan_available_funds_for_display(access_token) if access_token else None

    return jsonify({
        "open": open_trades,
        "closed": closed_trades,
        "current_capital": round(get_current_capital(), 2),
        "live_trading_enabled": get_live_trading_enabled(),
        "live_open": live_stats["live_open"],
        "live_closed": live_stats["live_closed"],
        "live_pnl": live_stats["live_pnl"],
        "live_available_funds": live_available_funds,
    })


@app.route("/api/paper-trading/settings", methods=["POST"])
def paper_trading_settings():
    data = request.get_json(silent=True) or {}
    token = (data.get("access_token") or "").strip()
    if not token:
        return jsonify({"status": "error", "message": "No token provided"}), 400
    set_setting("dhan_access_token", token)
    return jsonify({"status": "ok"})


@app.route("/api/paper-trading/capital", methods=["POST"])
def paper_trading_capital():
    data = request.get_json(silent=True) or {}
    try:
        capital = float(data.get("capital"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid amount"}), 400
    if capital <= 0:
        return jsonify({"status": "error", "message": "Amount must be positive"}), 400
    set_setting("paper_trade_capital", str(capital))
    return jsonify({"status": "ok", "capital": capital})


@app.route("/api/paper-trading/live-toggle", methods=["POST"])
def paper_trading_live_toggle():
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get("enabled"))
    set_setting("live_trading_enabled", "true" if enabled else "false")
    return jsonify({"status": "ok", "live_trading_enabled": enabled})


@app.route("/api/paper-trading/reset", methods=["POST"])
def paper_trading_reset():
    with get_db() as conn:
        conn.execute("DELETE FROM paper_trades")
        conn.commit()
    return jsonify({"status": "ok"})


@app.route("/api/paper-trading/manual-exit/<int:trade_id>", methods=["POST"])
def paper_trading_manual_exit(trade_id):
    with get_db() as conn:
        trade = conn.execute(
            "SELECT * FROM paper_trades WHERE id = ? AND status = 'OPEN'", (trade_id,)
        ).fetchone()
    if not trade:
        return jsonify({"status": "error", "message": "Trade not found or already closed"}), 404

    exit_price = None
    access_token = get_setting("dhan_access_token")
    if access_token:
        try:
            instrument_key = trade["paper_instrument_key"] or get_instrument_key(trade["symbol"])
            if instrument_key:
                candles = fetch_5min_candles(instrument_key, access_token)
                if candles:
                    exit_price = candles[-1][3]
        except Exception:
            pass

    if exit_price is None:
        exit_price = trade["last_checked_price"]
    if exit_price is None:
        return jsonify({"status": "error", "message": "No price available - save a token and run Check Exits Now at least once first"}), 400

    entry_price = trade["entry_price"]
    qty = trade["quantity"] or 1
    if trade["direction"] == "Buy":
        pnl = (exit_price - entry_price) * qty
    else:
        pnl = (entry_price - exit_price) * qty
    pnl = round(pnl, 2)
    capital_used = entry_price * qty
    pnl_pct = round((pnl / capital_used) * 100, 2) if capital_used else 0
    now = datetime.utcnow().isoformat()

    _close_live_position_if_any(trade, access_token)

    with get_db() as conn:
        conn.execute(
            """
            UPDATE paper_trades
            SET status = 'CLOSED', exit_price = ?, exit_time = ?,
                pnl = ?, pnl_pct = ?, exit_reason = ?, last_checked_time = ?
            WHERE id = ?
            """,
            (exit_price, now, pnl, pnl_pct, "Manual exit", now, trade_id),
        )
        conn.commit()

    return jsonify({"status": "ok", "exit_price": exit_price, "pnl": pnl, "pnl_pct": pnl_pct})


@app.route("/api/paper-trading/check", methods=["POST"])
def paper_trading_check():
    result = run_paper_trade_check()
    return jsonify(result)


@app.route("/api/paper-trading/debug-instruments")
def debug_instruments():
    _load_instrument_master()
    return jsonify({"equities": _instrument_debug, "options": _option_debug})


@app.route("/api/paper-trading/debug-atm")
def debug_atm():
    symbol = request.args.get("symbol", "")
    try:
        price = float(request.args.get("price", ""))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Pass ?symbol=X&price=Y in the URL"})
    _load_instrument_master()
    return jsonify({
        "symbol": symbol.upper(),
        "reference_price": price,
        "chain_length": len(_option_chain_cache.get(symbol.upper(), [])),
        "atm_call": get_atm_option(symbol, "CE", price),
        "atm_put": get_atm_option(symbol, "PE", price),
    })


@app.route("/api/paper-trading/debug-funds")
def debug_funds():
    access_token = get_setting("dhan_access_token")
    if not access_token:
        return jsonify({"ok": False, "error": "No Dhan access token saved"})
    value = get_dhan_available_funds(access_token)
    return jsonify({"value": value, **_funds_debug})


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
