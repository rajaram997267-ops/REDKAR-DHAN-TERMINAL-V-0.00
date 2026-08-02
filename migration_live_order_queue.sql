-- live_order_queue: the bridge between Render (webhook/dashboard/paper trading,
-- unaffected by the static-IP issue) and a scheduled script on Dhan Cloud
-- (which actually talks to Dhan's trading API, from Dhan's own trusted infra
-- so no IP whitelisting is needed).
--
-- Render INSERTs a row whenever a live action is needed. The Dhan Cloud
-- script (running once a minute) SELECTs status='PENDING' rows, processes
-- them, and UPDATEs status + result columns. Render's dashboard just reads
-- these same columns back to show live_status/live_error same as today.

CREATE TABLE IF NOT EXISTS live_order_queue (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER NOT NULL,          -- paper_trades.id this action belongs to
    action TEXT NOT NULL,               -- 'PLACE' or 'CLOSE'
    symbol TEXT,                        -- underlying symbol (needed for PLACE)
    direction TEXT,                     -- 'Buy' or 'Sell' (needed for PLACE, to pick CE/PE)
    reference_price TEXT,               -- alert trigger price (needed for PLACE, for ATM selection)
    security_id TEXT,                   -- the exact contract's Dhan securityId (needed for CLOSE)
    quantity INTEGER,                   -- the exact quantity to close (needed for CLOSE)
    status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING -> DONE or FAILED
    result_order_id TEXT,
    result_error TEXT,
    created_at TEXT NOT NULL,
    processed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_live_order_queue_pending
    ON live_order_queue (status) WHERE status = 'PENDING';
