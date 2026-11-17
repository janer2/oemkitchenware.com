-- One row per click on a contact link (WhatsApp), plus the page it came from.
-- Nothing here identifies a person on its own: sid is random per browser tab,
-- the IP is stored only as a salted hash, and the country comes from the edge.
CREATE TABLE IF NOT EXISTS wa_clicks (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  sid       TEXT NOT NULL,
  path      TEXT NOT NULL,
  referrer  TEXT,
  ts        INTEGER NOT NULL,
  width     INTEGER,
  lang      TEXT,
  country   TEXT,
  city      TEXT,
  ua        TEXT,
  ip_hash   TEXT
);

CREATE INDEX IF NOT EXISTS idx_wa_sid ON wa_clicks (sid);
CREATE INDEX IF NOT EXISTS idx_wa_ts  ON wa_clicks (ts);

-- When a buyer actually writes, paste the [sid] you see in their message here
-- and the click history for that enquiry appears. Kept in a separate table so
-- the click log stays anonymous if you never link it.
CREATE TABLE IF NOT EXISTS wa_links (
  sid        TEXT PRIMARY KEY,
  enquiry_at INTEGER NOT NULL,
  note       TEXT
);
