"""SQLite storage. One writer lock, WAL mode, safe to read while the runner is live."""
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen(
  mint TEXT PRIMARY KEY, first_seen REAL, source TEXT, decision TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS tokens(
  mint TEXT PRIMARY KEY, symbol TEXT, name TEXT, pair TEXT, dex TEXT, source TEXT,
  t0 REAL, price0 REAL, liq0 REAL, snapshot TEXT, snapshot_sha TEXT, card TEXT,
  promo TEXT, rugcheck_score REAL);
CREATE TABLE IF NOT EXISTS responses(
  id INTEGER PRIMARY KEY AUTOINCREMENT, mint TEXT, model TEXT, model_id TEXT, cond TEXT,
  messages TEXT, prompt_sha TEXT, text TEXT, response_sha TEXT,
  p_collapse_6h REAL, p_halve_6h REAL, p_collapse_24h REAL, action TEXT, risk_on INTEGER,
  created REAL, latency REAL, tok_in INTEGER, tok_out INTEGER, cost REAL, error TEXT,
  leaf TEXT, batch INTEGER, UNIQUE(mint, model, cond));
CREATE TABLE IF NOT EXISTS obs(
  mint TEXT, ts REAL, found INTEGER, price REAL, liq REAL, n_pairs INTEGER,
  PRIMARY KEY(mint, ts));
CREATE TABLE IF NOT EXISTS batches(
  id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL, kind TEXT, n INTEGER, root TEXT,
  leaves TEXT, tx TEXT, chain_id INTEGER, note TEXT);
CREATE TABLE IF NOT EXISTS outcomes(
  mint TEXT, horizon TEXT, obs_ts REAL, price_ratio REAL, liq_ratio REAL, vanished INTEGER,
  collapse INTEGER, halve INTEGER, strict INTEGER, PRIMARY KEY(mint, horizon));
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE INDEX IF NOT EXISTS obs_mint ON obs(mint, ts);
CREATE INDEX IF NOT EXISTS resp_batch ON responses(batch);
"""


class DB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA busy_timeout=10000")
            self.conn.executescript(SCHEMA)

    def x(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args)

    def q(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args).fetchall()

    def one(self, sql, args=()):
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def meta_get(self, k, default=None):
        r = self.one("SELECT v FROM meta WHERE k=?", (k,))
        return r["v"] if r else default

    def meta_set(self, k, v):
        self.x("INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))
