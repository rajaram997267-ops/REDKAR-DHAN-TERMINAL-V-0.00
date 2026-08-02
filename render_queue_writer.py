"""
render_queue_writer.py

Replaces the live-trading blocks in main.py's create_paper_trades_for_batch()
and _close_live_position_if_any() with queue inserts, since Render should no
longer call Dhan's trading API directly (that's the whole point of the
split - only the Dhan Cloud script does that, from Dhan's trusted infra).

Render's job is now just: decide WHAT should happen (place this ATM CE/PE,
or close this specific contract) and write it to live_order_queue. The
Dhan Cloud script (dhan_cloud_main.py) does the actual Dhan API calls and
writes the live_status/live_error/etc. columns on paper_trades directly -
so your dashboard queries (paper_trading_data(), etc.) need ZERO changes,
they just keep reading paper_trades as before.
"""

from datetime import datetime


def queue_live_place(conn, trade_id: int, symbol: str, direction: str, reference_price: float) -> None:
    """Call this from create_paper_trades_for_batch() in place of the old
    block that called get_atm_option/get_ltp/get_upstox_available_funds/
    place_live_order directly. Same trigger condition: only when
    get_live_trading_enabled() is True."""
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO live_order_queue
            (trade_id, action, symbol, direction, reference_price, status, created_at)
        VALUES (?, 'PLACE', ?, ?, ?, 'PENDING', ?)
        """,
        (trade_id, symbol, direction, str(reference_price), now),
    )
    conn.commit()
    # Optimistic UI state - the Dhan Cloud script will overwrite this with
    # the real outcome (OPEN/FAILED) within the next scheduled run.
    conn.execute(
        "UPDATE paper_trades SET live_status = 'PENDING' WHERE id = ?",
        (trade_id,),
    )
    conn.commit()


def queue_live_close(conn, trade_id: int, security_id: str, quantity: int) -> None:
    """Call this from _close_live_position_if_any() in place of the old
    direct place_live_order(..., 'SELL', ...) call. security_id and
    quantity come from the SAME trade row (live_instrument_key,
    live_quantity) - closing the exact contract that was bought, same as
    the current logic does."""
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO live_order_queue
            (trade_id, action, security_id, quantity, status, created_at)
        VALUES (?, 'CLOSE', ?, ?, 'PENDING', ?)
        """,
        (trade_id, security_id, quantity, now),
    )
    conn.commit()


def get_queue_status_for_trade(conn, trade_id: int) -> dict | None:
    """Optional helper for a 'live order status' debug view - shows the
    most recent queue row for a trade, in case live_status on paper_trades
    alone isn't enough detail while debugging."""
    row = conn.execute(
        "SELECT * FROM live_order_queue WHERE trade_id = ? ORDER BY id DESC LIMIT 1",
        (trade_id,),
    ).fetchone()
    return dict(row) if row else None
