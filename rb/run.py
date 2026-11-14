"""The runner: discover tokens, freeze a snapshot, ask every model under every
condition, commit hashes on-chain every hour, and keep tracking prices for 25 hours.

Every step is wrapped so one failure never stops the loop. Safe to kill and restart:
nothing is asked twice and nothing already committed changes.
"""
import datetime as dt
import json
import logging
import os
import random
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import merkle, prompts
from .sources import aggregate, build_snapshot, canon, enrich, pairs_of, render_card, sha

log = logging.getLogger("rb")
PREREG_FILES = ["PREREG.md", "config.yaml", os.path.join("rb", "prompts.py")]


def parse_time(s):
    return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()


def chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


class Runner:
    def __init__(self, cfg, db, dex, rc, models, anchor, extra_sources=None, clock=time.time, root_dir="."):
        self.cfg, self.db, self.dex, self.rc = cfg, db, dex, rc
        self.models = [m for m in models if m.ready]
        self.anchor, self.clock, self.root_dir = anchor, clock, root_dir
        r = cfg["run"]
        self.collect_until = parse_time(r["collect_until"])
        self.batch_size = int(r.get("dex_batch", 10))
        self.budget = float(r.get("budget_usd", 20))
        self.rng = random.Random(int(r.get("seed", 20261114)))
        self.pool = ThreadPoolExecutor(max_workers=int(r.get("concurrency", 12)))
        self.spent = float(db.one("SELECT COALESCE(SUM(cost),0) s FROM responses")["s"])
        self.spent_lock = threading.Lock()
        self.stop = False
        self.sources = []
        wanted = cfg.get("sources") or ["dexscreener_profiles"]
        if "dexscreener_profiles" in wanted:
            self.sources.append(("dexscreener_profiles", dex.profiles))
        if "dexscreener_boosts" in wanted:
            self.sources.append(("dexscreener_boosts", dex.boosts))
        for name, fn in (extra_sources or []):
            if name in wanted:
                self.sources.append((name, fn))

    # ---------- discovery ----------

    def collecting(self, now):
        if now >= self.collect_until:
            return False
        if self.spent >= self.budget:
            return False
        n = self.db.one("SELECT COUNT(*) c FROM tokens")["c"]
        return n < int(self.cfg["run"].get("max_tokens_total", 500))

    def pairs_for(self, mints):
        """mint -> list of pairs. A mint missing from a batch reply is asked for again
        on its own before we believe it has no pairs. Mints whose lookup failed are
        left out of the result entirely (unknown is not the same as gone)."""
        out = {}
        for chunk in chunks(list(mints), self.batch_size):
            try:
                pairs = self.dex.tokens(chunk)
            except Exception as e:
                log.warning("dexscreener batch failed: %s", e)
                continue
            for m in chunk:
                ps = pairs_of(m, pairs)
                if not ps and len(chunk) > 1:
                    try:
                        ps = pairs_of(m, self.dex.tokens([m]))
                    except Exception:
                        continue
                out[m] = ps
        return out

    def _recheckable(self, mint):
        """A candidate is worth evaluating if it is new, or was previously rejected for a
        reason that can still change (liquidity can grow past the threshold, a pair can
        appear, an hourly cap frees up). Already-accepted tokens are never re-added, and
        a token that has aged out of the window cannot come back. This re-evaluates the
        inclusion filter on every poll rather than only at first sighting; the $10k
        definition of "accepted" is unchanged. Deviation from PREREG; see DEVIATIONS.md."""
        r = self.db.one("SELECT decision, reason FROM seen WHERE mint=?", (mint,))
        if r is None:
            return True
        return r["decision"] != "accepted" and r["reason"] != "too_old"

    def discover(self):
        now = self.clock()
        if not self.collecting(now):
            return 0
        cands = {}
        for name, fn in self.sources:
            try:
                for mint, promo in fn():
                    cands.setdefault(mint, (name, promo))
            except Exception as e:
                log.warning("source %s failed: %s", name, e)
        new = [m for m in cands if self._recheckable(m)]
        self.rng.shuffle(new)
        cap = int(self.cfg["run"].get("max_tokens_per_hour", 60))
        added = 0
        for mint, ps in self.pairs_for(new).items():
            src, promo = cands[mint]
            ok, reason, snap = build_snapshot(mint, ps, now, self.cfg.get("filters") or {})
            if reason == "too_new":
                continue  # look again next cycle
            if ok and self.db.one("SELECT COUNT(*) c FROM tokens WHERE t0>?", (now - 3600,))["c"] >= cap:
                ok, reason = False, "hourly_cap"
            if ok and not self.collecting(now):
                break
            self.db.x("INSERT INTO seen(mint,first_seen,source,decision,reason) VALUES(?,?,?,?,?) "
                      "ON CONFLICT(mint) DO UPDATE SET source=excluded.source, "
                      "decision=excluded.decision, reason=excluded.reason",
                      (mint, now, src, "accepted" if ok else "rejected", reason))
            if not ok:
                continue
            score = enrich(snap, self.rc.report(mint))
            promo = promo if len(promo) >= prompts.PROMO_MIN else ""
            snap["source"] = src
            snap["promo_sha"] = sha(promo) if promo else None
            snap_json = canon(snap)
            self.db.x("INSERT OR IGNORE INTO tokens VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (mint, snap["symbol"], snap["name"], snap["pair"], snap["dex"], src, now,
                       snap["price_usd"], snap["liquidity_usd"], snap_json, sha(snap_json),
                       render_card(snap), promo, score))
            self.db.x("INSERT OR REPLACE INTO obs VALUES(?,?,?,?,?,?)",
                      (mint, now, 1, snap["price_usd"], snap["liquidity_usd"], snap["n_pairs"]))
            for mc in self.models:
                self.pool.submit(self.ask_model, mint, mc)
            added += 1
        if added:
            log.info("accepted %d new tokens (total %d, spent $%.2f)", added,
                     self.db.one("SELECT COUNT(*) c FROM tokens")["c"], self.spent)
        return added

    # ---------- asking models ----------

    def ask(self, tok, mc, cond, messages):
        done = self.db.one("SELECT text, risk_on FROM responses WHERE mint=? AND model=? AND cond=?",
                           (tok["mint"], mc.name, cond))
        if done:
            return dict(done)
        if self.spent >= self.budget:
            return None
        out = mc.chat(messages)
        parsed = prompts.parse(out["text"])
        if parsed is None and out["text"]:  # one more try if the format was not followed
            again = mc.chat(messages)
            out["cost"] += again["cost"]
            out["tok_in"] += again["tok_in"]
            out["tok_out"] += again["tok_out"]
            p2 = prompts.parse(again["text"])
            if p2 is not None:
                parsed = p2
                out["text"], out["latency"], out["error"] = again["text"], again["latency"], None
        with self.spent_lock:
            self.spent += out["cost"]
        created = self.clock()
        msg_json = canon(messages)
        psha, rsha = sha(msg_json), sha(out["text"])
        leaf = sha(canon({"mint": tok["mint"], "model_id": mc.model, "cond": cond,
                          "snapshot_sha": tok["snapshot_sha"], "prompt_sha": psha,
                          "response_sha": rsha, "created": int(created)})) if out["text"] else None
        p = parsed or {}
        err = out["error"] or (None if parsed else "unparsed")
        self.db.x(
            "INSERT OR IGNORE INTO responses(mint,model,model_id,cond,messages,prompt_sha,text,response_sha,"
            "p_collapse_6h,p_halve_6h,p_collapse_24h,action,risk_on,created,latency,tok_in,tok_out,cost,error,leaf)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tok["mint"], mc.name, mc.model, cond, msg_json, psha, out["text"], rsha,
             p.get("p_collapse_6h"), p.get("p_halve_6h"), p.get("p_collapse_24h"), p.get("action"),
             p.get("risk_on"), int(created), out["latency"], out["tok_in"], out["tok_out"], out["cost"], err, leaf))
        return {"text": out["text"], "risk_on": p.get("risk_on")}

    def ask_model(self, mint, mc):
        try:
            tok = dict(self.db.one("SELECT * FROM tokens WHERE mint=?", (mint,)))
            a_msgs = prompts.first_turn("A", tok["card"])
            a = self.ask(tok, mc, "A", a_msgs)
            self.ask(tok, mc, "B", prompts.first_turn("B", tok["card"]))
            self.ask(tok, mc, "C", prompts.first_turn("C", tok["card"]))
            if tok["promo"]:
                self.ask(tok, mc, "P", prompts.first_turn("P", tok["card"], tok["promo"]))
            if a and a["text"] and a["risk_on"] is not None:
                for cond in ("D", "D0"):
                    self.ask(tok, mc, cond, prompts.follow_up(cond, a_msgs, a["text"], a["risk_on"]))
        except Exception:
            log.exception("ask_model %s %s", mint, mc.name)

    def resume(self):
        """After a restart, finish tokens whose snapshot is still fresh (10 minutes)."""
        for r in self.db.q("SELECT mint FROM tokens WHERE t0>?", (self.clock() - 600,)):
            for mc in self.models:
                self.pool.submit(self.ask_model, r["mint"], mc)

    # ---------- price tracking ----------

    def track(self):
        now = self.clock()
        horizon = float(self.cfg["run"].get("track_hours", 25.5)) * 3600
        mints = [r["mint"] for r in self.db.q("SELECT mint FROM tokens WHERE t0>?", (now - horizon,))]
        n = 0
        for mint, ps in self.pairs_for(mints).items():
            best, price, liq = aggregate(ps)
            found = 1 if best is not None else 0
            self.db.x("INSERT OR REPLACE INTO obs VALUES(?,?,?,?,?,?)", (mint, now, found, price, liq, len(ps)))
            n += 1
        log.info("tracked %d/%d tokens", n, len(mints))
        return n

    # ---------- commitments ----------

    def commit_prereg(self):
        if self.db.one("SELECT 1 FROM batches WHERE kind='prereg'"):
            return None
        hashes = {}
        for f in PREREG_FILES:
            with open(os.path.join(self.root_dir, f), "rb") as fh:
                hashes[f] = sha(fh.read())
        leaves = [hashes[f] for f in PREREG_FILES]
        return self._store_batch("prereg", leaves, json.dumps(hashes))

    def commit(self):
        rows = self.db.q("SELECT id, leaf FROM responses WHERE batch IS NULL AND leaf IS NOT NULL ORDER BY id")
        if not rows:
            return None
        bid = self._store_batch("responses", [r["leaf"] for r in rows], None)
        self.db.x(f"UPDATE responses SET batch=? WHERE id IN ({','.join('?' * len(rows))})",
                  [bid] + [r["id"] for r in rows])
        return bid

    def _store_batch(self, kind, leaves, note):
        root = merkle.root([bytes.fromhex(x) for x in leaves]).hex()
        cur = self.db.x("INSERT INTO batches(created,kind,n,root,leaves,chain_id,note) VALUES(?,?,?,?,?,?,?)",
                        (self.clock(), kind, len(leaves), root, json.dumps(leaves), self.anchor.chain_id, note))
        log.info("batch %d (%s): %d leaves, root %s", cur.lastrowid, kind, len(leaves), root)
        self.anchor_pending()
        return cur.lastrowid

    def anchor_pending(self):
        if not self.anchor.enabled:
            return
        for b in self.db.q("SELECT id, root FROM batches WHERE tx IS NULL ORDER BY id"):
            try:
                tx = self.anchor.send(b["root"])
                self.db.x("UPDATE batches SET tx=? WHERE id=?", (tx, b["id"]))
                log.info("batch %d anchored: %s", b["id"], tx)
            except Exception as e:
                log.warning("anchoring batch %d failed, will retry: %s", b["id"], e)
                return

    # ---------- main loop ----------

    def _safe(self, fn):
        try:
            return fn()
        except Exception:
            log.exception("%s failed", fn.__name__)

    def loop(self):
        r = self.cfg["run"]
        poll, trk, cmt = int(r.get("poll_seconds", 180)), int(r.get("track_seconds", 600)), int(r.get("commit_seconds", 3600))

        def _stop(*_):
            self.stop = True
        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)

        if not self.models:
            log.error("no model is ready: set API keys in .env and model ids in config.yaml")
        log.info("models: %s | anchoring: %s | collecting until %s UTC | budget $%.2f",
                 [m.name for m in self.models], "on" if self.anchor.enabled else "OFF (roots stored locally only)",
                 dt.datetime.fromtimestamp(self.collect_until, dt.timezone.utc).strftime("%Y-%m-%d %H:%M"), self.budget)
        self._safe(self.commit_prereg)
        self.resume()
        now = self.clock()
        nxt = {"discover": now, "track": now + trk, "commit": now + cmt, "anchor": now + 300}
        while not self.stop:
            now = self.clock()
            if now >= nxt["discover"]:
                self._safe(self.discover)
                nxt["discover"] = now + poll
            if now >= nxt["track"]:
                self._safe(self.track)
                nxt["track"] = now + trk
            if now >= nxt["commit"]:
                self._safe(self.commit)
                nxt["commit"] = now + cmt
            if now >= nxt["anchor"]:
                self._safe(self.anchor_pending)
                nxt["anchor"] = now + 300
            time.sleep(2)
        log.info("stopping: waiting for in-flight model calls, then committing")
        self.pool.shutdown(wait=True)
        self._safe(self.commit)
