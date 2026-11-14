"""Offline end-to-end test: fake market, fake models, fake chain, simulated clock.
Run from the project root:  python -m tests.test_offline
"""
import json
import os
import re
import shutil
import sys
import tempfile

from rb import merkle, prompts, report, resolve
from rb.anchor import BaseAnchor, calldata
from rb.db import DB
from rb.run import Runner
from rb.sources import canon, sha

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = 1_794_700_000.0


class Clock:
    def __init__(self):
        self.t = T0

    def __call__(self):
        return self.t


class FakeDex:
    """Ten tokens. Even ones collapse after 3h, token 4 loses all pools after 5h,
    token 9 is illiquid from the start, token 8 migrates pools (must NOT count as a pull)."""

    def __init__(self, clock):
        self.clock, self.fail = clock, False
        self.mints = [f"Mint{i:02d}pump" for i in range(10)]

    def profiles(self):
        return [(m, "The most based cat on Solana. Community owned, devs locked, 1000x incoming!" if i % 3 == 0 else "")
                for i, m in enumerate(self.mints)]

    def boosts(self):
        return [(self.mints[0], "")]

    def tokens(self, mints):
        if self.fail:
            raise RuntimeError("simulated outage")
        age_h = (self.clock() - T0) / 3600.0
        out = []
        for m in mints:
            i = self.mints.index(m)
            price, liq = 0.001 * (i + 1), 30000.0
            if i == 9:
                liq = 800.0
            if i % 2 == 0 and age_h >= 3:
                price, liq = price * 0.04, liq * 0.1
            if i == 4 and age_h >= 5:
                continue
            pools = [("pumpswap", liq)]
            if i == 8 and age_h >= 2:  # liquidity split across two pools after a migration
                pools = [("pumpswap", liq * 0.1), ("raydium", liq * 0.9)]
            for dex, l in pools:
                out.append({"chainId": "solana", "dexId": dex, "pairAddress": f"pair{i}{dex}",
                            "baseToken": {"address": m, "symbol": f"T{i}", "name": f"Token {i}"},
                            "quoteToken": {"symbol": "SOL"}, "priceUsd": str(price),
                            "liquidity": {"usd": l}, "marketCap": 50000, "pairCreatedAt": (T0 - 1800) * 1000,
                            "txns": {"m5": {"buys": 5, "sells": 4}, "h1": {"buys": 80, "sells": 60}},
                            "volume": {"m5": 900, "h1": 21000, "h6": 21000},
                            "priceChange": {"m5": 1.5, "h1": 40.0, "h6": 40.0},
                            "info": {"socials": [{"type": "twitter"}]}, "boosts": {"active": 10}})
        return out


class FakeRug:
    def report(self, mint):
        i = int(mint[4:6])
        if i == 7:
            return None  # RugCheck has not indexed this one
        return {"knownAccounts": {"POOL": {"name": "AMM"}}, "token": {"supply": 1e15},
                "topHolders": [{"address": "POOL", "pct": 20.0}] + [{"address": f"h{k}", "owner": f"o{k}", "pct": 3.0} for k in range(12)],
                "creatorBalance": 1e13, "mintAuthority": None, "freezeAuthority": None, "tokenMeta": {"mutable": False},
                "markets": [{"lp": {"quoteUSD": 100, "baseUSD": 100, "lpLockedPct": 100}}], "totalHolders": 300,
                "graphInsidersDetected": 3, "transferFee": {"pct": 0}, "launchpad": {"name": "Pump.Fun"},
                "score_normalised": 70 if i % 2 == 0 else 20}


class FakeModel:
    """Sycophantic by construction, so every contrast has a known sign."""
    ready, key_env = True, "X"

    def __init__(self, name, refuse_on=None):
        self.name, self.model, self.refuse_on, self.calls = name, f"fake/{name}", refuse_on, 0

    def chat(self, messages, tries=3):
        self.calls += 1
        if self.refuse_on and self.refuse_on in messages[0]["content"]:
            return {"text": "I can't give financial advice.", "tok_in": 500, "tok_out": 10, "cost": 0.001, "latency": 0.1, "error": None}
        first, last = messages[0]["content"], messages[-1]["content"]
        risky = int(re.search(r"Token: Token (\d+)", first).group(1)) % 2 == 0
        p = 0.7 if risky else 0.3
        hold = "Should I hold or sell" in first
        if "going to 100x" in first:
            p -= 0.25
        if hold:
            p -= 0.2
        if "describes itself" in first:
            p -= 0.1
        if "too negative" in last:
            p -= 0.3
        if "too risky to me" in last:
            p += 0.3
        p = min(0.99, max(0.01, p))
        on = p < 0.5
        action = ("hold" if on else "sell") if hold else ("buy" if on else "avoid")
        text = f"Here is my view.\n{{\"action\": \"{action}\", \"p_collapse_6h\": {p:.2f}, \"p_halve_6h\": {min(1, p + .1):.2f}, \"p_collapse_24h\": \"{min(99, p * 100 + 5):.0f}%\"}}"
        return {"text": text, "tok_in": 600, "tok_out": 120, "cost": 0.002, "latency": 0.1, "error": None}


class FakeAnchor:
    enabled, chain_id = True, 8453

    def __init__(self):
        self.sent, self.fail = [], False

    def send(self, root_hex):
        if self.fail:
            raise RuntimeError("rpc down")
        self.sent.append(root_hex)
        return "0x" + sha(root_hex)[:64]


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit(1)


def unit_tests():
    for n in range(1, 34):
        leaves = [sha(str(i)).encode() for i in range(n)]
        r = merkle.root(leaves)
        assert all(merkle.root_from_path(i, n, leaves[i], merkle.path(i, leaves)) == r for i in range(n)), n
        if n > 1:
            assert merkle.root_from_path(0, n, leaves[1], merkle.path(0, leaves)) != r
    check(True, "Merkle proofs verify for every leaf of trees with 1..33 leaves, and reject a wrong leaf")
    check(merkle.root([b""]).hex() == "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d",
          "Merkle leaf hash matches the RFC 6962 test vector")
    p = prompts.parse('Sure.\n{"action": "Buy", "p_collapse_6h": 35, "p_halve_6h": "0.5", "p_collapse_24h": "60%"}')
    check(p == {"action": "buy", "risk_on": 1, "p_collapse_6h": 0.35, "p_halve_6h": 0.5, "p_collapse_24h": 0.6},
          "parser handles percent, string numbers and capitalised actions")
    check(prompts.parse("I can't help with that.") is None and prompts.parse('{"p_collapse_6h": "high"}') is None,
          "parser returns None for refusals and non-numeric answers")
    check(prompts.parse('{"action":"maybe","p_collapse_6h":0.4}')["risk_on"] is None, "unknown action is kept as missing, not guessed")
    a = prompts.first_turn("A", "CARD")[0]["content"]
    c = prompts.first_turn("C", "CARD")[0]["content"]
    check('"buy" or "avoid"' in a and '"hold" or "sell"' in c and "CARD" in a, "prompts render with the right action pair")
    os.environ["TEST_KEY"] = "0x" + "11" * 32
    anc = BaseAnchor({"key_env": "TEST_KEY"}, None)
    raw = anc.sign(anc.build("ab" * 32, 0, 10_000_000, 1_000_000, 40_000))
    check(raw.startswith("0x02") and ("ab" * 32) in raw and calldata("ab" * 32)[2:] in raw,
          "anchor transaction signs offline as an EIP-1559 tx carrying the tagged root")


def end_to_end():
    tmp = tempfile.mkdtemp()
    try:
        for f in ("PREREG.md", "config.yaml"):
            shutil.copy(os.path.join(ROOT, f), tmp)
        os.makedirs(os.path.join(tmp, "rb"))
        shutil.copy(os.path.join(ROOT, "rb", "prompts.py"), os.path.join(tmp, "rb"))
        clock = Clock()
        cfg = {"run": {"collect_until": "2030-01-01T00:00:00Z", "max_tokens_per_hour": 8, "budget_usd": 5, "concurrency": 4},
               "sources": ["dexscreener_profiles", "dexscreener_boosts"],
               "filters": {"min_liquidity_usd": 10000, "min_age_minutes": 5, "max_age_hours": 24, "min_txns_h1": 20}}
        db = DB(os.path.join(tmp, "t.sqlite"))
        dex, anchor = FakeDex(clock), FakeAnchor()
        models = [FakeModel("alpha"), FakeModel("beta", refuse_on="Token 5")]
        r = Runner(cfg, db, dex, FakeRug(), models, anchor, clock=clock, root_dir=tmp)

        r.commit_prereg()
        check(db.one("SELECT COUNT(*) c FROM batches WHERE kind='prereg' AND tx IS NOT NULL")["c"] == 1, "pre-registration hash anchored first")
        added = r.discover()
        r.pool.shutdown(wait=True)
        check(added == 8, f"8 tokens accepted under the hourly cap (got {added})")
        reasons = {x["reason"]: x["c"] for x in db.q("SELECT reason, COUNT(*) c FROM seen GROUP BY reason")}
        check(reasons.get("accepted") == 8 and reasons.get("low_liquidity", 0) + reasons.get("hourly_cap", 0) == 2,
              f"every screened token has a logged decision {reasons}")
        n = db.one("SELECT COUNT(*) c FROM responses")["c"]
        npromo = db.one("SELECT COUNT(*) c FROM tokens WHERE promo!=''")["c"]
        check(db.one("SELECT COUNT(*) c FROM responses WHERE model='alpha'")["c"] == 8 * 5 + npromo,
              f"model alpha answered A,B,C,D,D0 for 8 tokens plus P for {npromo} with a description")
        ref = db.q("SELECT cond FROM responses WHERE error='unparsed' AND model='beta'")
        check(sorted(x["cond"] for x in ref) == ["A", "B", "C"], "a refusal is retried once, then stored and flagged; no follow-up is sent after a refused first answer")
        card = db.one("SELECT card FROM tokens LIMIT 1")["card"]
        check("score" not in card.lower() and "Top 10 wallets hold 30.0%" in card, "card excludes the pool from top-10 and hides RugCheck's score")

        r2 = Runner(cfg, db, dex, FakeRug(), models, anchor, clock=clock, root_dir=tmp)
        r2.discover(); r2.resume(); r2.pool.shutdown(wait=True)
        check(db.one("SELECT COUNT(*) c FROM responses")["c"] == n, "restart asks nothing twice")

        anchor.fail = True
        bid = r2.commit()
        check(db.one("SELECT tx FROM batches WHERE id=?", (bid,))["tx"] is None, "RPC failure leaves the batch stored and unanchored")
        anchor.fail = False
        r2.anchor_pending()
        check(db.one("SELECT tx FROM batches WHERE id=?", (bid,))["tx"] is not None, "unanchored batch is retried and anchored")
        check(db.one("SELECT COUNT(*) c FROM responses WHERE batch IS NULL AND leaf IS NOT NULL")["c"] == 0, "all responses committed")

        # independent recomputation of one leaf and its proof from raw stored data
        row = db.one("SELECT * FROM responses WHERE cond='D' LIMIT 1")
        tok = db.one("SELECT * FROM tokens WHERE mint=?", (row["mint"],))
        leaf = sha(canon({"mint": row["mint"], "model_id": row["model_id"], "cond": "D", "snapshot_sha": sha(tok["snapshot"]),
                          "prompt_sha": sha(row["messages"]), "response_sha": sha(row["text"]), "created": int(row["created"])}))
        b = db.one("SELECT * FROM batches WHERE id=?", (row["batch"],))
        leaves = [bytes.fromhex(x) for x in json.loads(b["leaves"])]
        i = leaves.index(bytes.fromhex(leaf))
        check(merkle.root_from_path(i, len(leaves), leaves[i], merkle.path(i, leaves)).hex() == b["root"] and b["root"] in anchor.sent,
              "a response re-hashed from raw data proves into the anchored root")
        check(len(json.loads(row["messages"])) == 3, "pushback is a real second turn carrying the model's own first answer")

        for hours in (1.0, 1.75, 3.5):
            clock.t = T0 + hours * 3600; r2.track()
        dex.fail = True
        clock.t = T0 + 4 * 3600; r2.track()
        dex.fail = False
        check(db.one("SELECT COUNT(*) c FROM obs WHERE ts=?", (clock.t,))["c"] == 0, "API outage records nothing (no false 'vanished')")
        for hours in (6.01, 6.75, 24.02, 24.8):
            clock.t = T0 + hours * 3600; r2.track()
        stats = resolve.resolve(db, clock.t)
        check(stats["6h"] == (8, 0, 0) and stats["24h"] == (8, 0, 0), f"all horizons resolved {stats}")
        o = {x["mint"]: dict(x) for x in db.q("SELECT * FROM outcomes WHERE horizon='6h'")}
        check(o["Mint04pump"]["vanished"] == 1 and o["Mint04pump"]["collapse"] == 1, "token with no pools left counts as collapsed")
        check(o["Mint08pump"]["liq_ratio"] > 0.05 and o["Mint08pump"]["collapse"] == 1 and o["Mint03pump"]["collapse"] == 0,
              "liquidity is summed across pools after a migration; untouched token is not collapsed")
        check(db.one("SELECT collapse FROM outcomes WHERE mint='Mint00pump' AND horizon='1h'")["collapse"] == 0, "1h label is taken before the collapse")
        check(o["Mint00pump"]["strict"] == 1, "strict label needs price and liquidity down and still down later")

        md = report.write(db, os.path.join(tmp, "results"))
        R = json.load(open(os.path.join(tmp, "results", "results.json")))
        A = R["models"]["alpha"]
        check(A["shift_p"]["B"]["mean"] < 0 and A["shift_p"]["C"]["mean"] < 0, "report recovers the built-in hype and sunk-cost shifts with the right sign")
        check(A["accuracy"]["p_collapse_6h"]["auc"] == 1.0 and A["accuracy"]["p_collapse_6h"]["n"] == 8, "AUC is 1.0 for a model built to rank perfectly")
        check(A["flip"]["after_risk_off"]["flip_rate_pressure"] == 1.0 and A["flip"]["after_risk_off"]["flip_rate_recheck"] == 0.0,
              "flip rate separates pressure from a plain re-check")
        check(A["brier_change"]["D"]["mean"] > 0, "pressure-induced change is scored against the real outcome (Brier worsens)")
        check(R["baseline_rugcheck_auc_6h"] is not None and "On-chain commitments" in md, "baseline and commitments are in the report")
        print("\n" + md[:1500])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unit_tests()
    end_to_end()
    print("\nALL OFFLINE TESTS PASSED")
