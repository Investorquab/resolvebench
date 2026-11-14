"""Command line: python -m rb <command>

  probe     check the data APIs and how many tokens pass the filter (no keys needed)
  catalog   list model ids and prices each configured provider offers
  models    send one real question to each configured model and show the parsed answer
  run       start collecting (the long-running process)
  status    counts, spend, commitments
  resolve   label outcomes from tracked prices
  report    resolve, then write results/report.md and results/results.json
  verify    prove one response was committed before its outcome
  export    write the public data files (responses, snapshots, outcomes, batches)
"""
import argparse
import datetime as dt
import json
import logging
import os
import sys
import time

import yaml

from . import merkle, prompts, report as report_mod, resolve as resolve_mod
from .anchor import calldata, lookup_tx, make_anchor
from .db import DB
from .models import ModelClient
from .run import Runner
from .sources import DexScreener, GeckoTerminal, Http, RugCheck, build_snapshot, canon, enrich, pairs_of, render_card, sha

SAMPLE_CARD = """Token: Example Cat (EXCAT) on Solana
Main pool: EXCAT/SOL on pumpswap, first traded 47 minutes ago
Price: $0.0000412 | Market cap: $41,200 | Pool liquidity: $18,450
Volume: $2,310 (5 min), $64,800 (1 hour), $64,800 (6 hours)
Trades: 412 buys / 367 sells (1 hour); 21 buys / 30 sells (5 min)
Price change: -6.2% (5 min), +38.0% (1 hour), +38.0% (6 hours)
Holders: 388 | Top 10 wallets hold 31.4% (liquidity pool excluded) | Creator holds 0.0%
Mint authority: revoked | Freeze authority: revoked | Metadata mutable: no
LP tokens locked or burned: 100.0% | Transfer tax: 0.0%
Wallets flagged as linked insiders: 6
Launchpad: Pump.Fun | Website: no | X account: yes | Telegram: no | Paid promotion on DexScreener: yes"""


def load(args):
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(args.dir, ".env"))
    except ImportError:
        pass
    with open(os.path.join(args.dir, "config.yaml")) as f:
        cfg = yaml.safe_load(f)
    http = Http()
    models = [ModelClient(m, http) for m in cfg.get("models") or [] if m.get("enabled", True)]
    return cfg, http, models


def open_db(cfg, args):
    path = os.path.join(args.dir, cfg["run"].get("db", "data/resolvebench.sqlite"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return DB(path)


def cmd_probe(args):
    cfg, http, _ = load(args)
    dex, rc, gt = DexScreener(http), RugCheck(http), GeckoTerminal(http)
    feeds = [("dexscreener_profiles", dex.profiles), ("dexscreener_boosts", dex.boosts), ("geckoterminal_new_pools", gt.new_pools)]
    seen, rounds = {}, max(1, args.minutes)
    for i in range(rounds):
        for name, fn in feeds:
            try:
                got = fn()
                fresh = [m for m, _ in got if m not in seen]
                for m, promo in got:
                    seen.setdefault(m, (name, promo))
                print(f"[{name}] {len(got)} Solana tokens, {len(fresh)} not seen before, "
                      f"{sum(1 for _, p in got if len(p) >= prompts.PROMO_MIN)} with a description")
            except Exception as e:
                print(f"[{name}] FAILED: {e}")
        if i + 1 < rounds:
            time.sleep(60)
    if args.minutes > 1:
        print(f"\n{len(seen)} distinct tokens in {args.minutes} min -> roughly {len(seen) / args.minutes * 60:.0f} candidates per hour")
    mints, now, flt = list(seen)[:args.limit], time.time(), cfg.get("filters") or {}
    reasons, liqs, passed = {}, [], []
    for i in range(0, len(mints), 10):
        try:
            pairs = dex.tokens(mints[i:i + 10])
        except Exception as e:
            print("pair lookup FAILED:", e)
            continue
        for m in mints[i:i + 10]:
            ps = pairs_of(m, pairs)
            ok, reason, snap = build_snapshot(m, ps, now, flt)
            reasons[reason] = reasons.get(reason, 0) + 1
            liqs.append(sum(float((p.get("liquidity") or {}).get("usd") or 0) for p in ps))
            if ok:
                passed.append(snap)
    print(f"\nChecked {len(mints)} tokens against the filter {flt}:")
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    for th in (2000, 5000, 10000, 20000, 50000):
        print(f"  liquidity >= ${th:,}: {sum(1 for x in liqs if x >= th)}")
    if passed:
        snap = passed[0]
        score = enrich(snap, rc.report(snap["mint"]))
        print(f"\nRugCheck reachable: {snap['rugcheck_ok']} (score {score})\n\nExample facts card:\n")
        print(render_card(snap))
        chg = [s["chg_h1"] for s in passed if s.get("chg_h1") is not None]
        print(f"\n{len(passed)} passed. Of those, 1-hour price change already below -50%: {sum(1 for c in chg if c <= -50)}")
    else:
        print("\nNothing passed the filter. Lower filters.min_liquidity_usd in config.yaml and probe again.")


def cmd_catalog(args):
    cfg, http, models = load(args)
    done = set()
    for m in models:
        if m.base_url in done:
            continue
        done.add(m.base_url)
        print(f"\n== {m.base_url}")
        try:
            data = (m.list_models() or {}).get("data", [])
        except Exception as e:
            print("  FAILED:", e)
            continue
        for d in sorted(data, key=lambda d: d.get("id", "")):
            mid = d.get("id", "")
            if args.filter and args.filter.lower() not in mid.lower():
                continue
            pr = d.get("pricing") or {}
            price = ""
            if pr.get("prompt") is not None:
                try:
                    price = f"  in ${float(pr['prompt']) * 1e6:.3f} / out ${float(pr['completion']) * 1e6:.3f} per 1M"
                except (TypeError, ValueError):
                    pass
            print(f"  {mid}{price}")


def cmd_models(args):
    cfg, http, models = load(args)
    msgs = prompts.first_turn("A", SAMPLE_CARD)
    for m in models:
        if not m.ready:
            print(f"[{m.name}] SKIPPED: set {m.key_env} in .env and a real model id in config.yaml")
            continue
        out = m.chat(msgs, tries=1)
        parsed = prompts.parse(out["text"])
        status = "OK" if parsed else "PROBLEM"
        print(f"[{m.name}] {status} | {m.model} | {out['latency']:.1f}s | {out['tok_in']} in / {out['tok_out']} out | ${out['cost']:.5f}")
        print(f"    parsed: {parsed}" if parsed else f"    error: {out['error']} | reply starts: {out['text'][:200]!r}")
        if parsed:
            per_token, n = out["cost"] * 6, int(cfg["run"].get("max_tokens_total", 150))
            print(f"    about ${per_token:.4f} per token for this model (6 calls), ${per_token * n:.2f} for the full {n} tokens")


def cmd_run(args):
    cfg, http, models = load(args)
    os.makedirs(os.path.join(args.dir, "data"), exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(os.path.join(args.dir, "data", "run.log"))])
    logging.getLogger("httpx").setLevel(logging.WARNING)
    db = open_db(cfg, args)
    gt = GeckoTerminal(http)
    Runner(cfg, db, DexScreener(http), RugCheck(http), models, make_anchor(cfg, http),
           extra_sources=[("geckoterminal_new_pools", gt.new_pools)], root_dir=args.dir).loop()


def cmd_status(args):
    cfg, http, _ = load(args)
    db = open_db(cfg, args)
    t = db.one("SELECT COUNT(*) c, MIN(t0) a, MAX(t0) b FROM tokens")
    r = db.one("SELECT COUNT(*) c, COALESCE(SUM(cost),0) s, SUM(error IS NOT NULL) e, SUM(batch IS NULL AND leaf IS NOT NULL) u FROM responses")
    ts = lambda x: dt.datetime.fromtimestamp(x, dt.timezone.utc).strftime("%m-%d %H:%M UTC") if x else "-"
    print(f"tokens: {t['c']} (first {ts(t['a'])}, last {ts(t['b'])}) | collecting until {cfg['run']['collect_until']}")
    print(f"responses: {r['c']} | failed or unparsed: {r['e'] or 0} | not yet committed: {r['u'] or 0} | spend ${r['s']:.2f} of ${cfg['run'].get('budget_usd')}")
    for m in db.q("SELECT model, COUNT(*) c, SUM(p_collapse_6h IS NOT NULL) ok, COALESCE(SUM(cost),0) s FROM responses GROUP BY model"):
        print(f"  {m['model']}: {m['c']} calls, {m['ok']} parsed, ${m['s']:.2f}")
    print(f"observations: {db.one('SELECT COUNT(*) c FROM obs')['c']} | outcomes: {db.one('SELECT COUNT(*) c FROM outcomes')['c']}")
    for b in db.q("SELECT * FROM batches ORDER BY id"):
        print(f"  batch {b['id']} {b['kind']}: {b['n']} records, {ts(b['created'])}, tx {b['tx'] or 'NOT ANCHORED'}")


def cmd_resolve(args):
    cfg, http, _ = load(args)
    for h, (ok, pending, missing) in resolve_mod.resolve(open_db(cfg, args), time.time()).items():
        print(f"{h}: {ok} resolved, {pending} pending, {missing} missing (tracker was down at the horizon)")


def cmd_report(args):
    cfg, http, _ = load(args)
    db = open_db(cfg, args)
    resolve_mod.resolve(db, time.time())
    print(report_mod.write(db, os.path.join(args.dir, "results"), (cfg.get("anchor") or {}).get("explorer", "")))


def cmd_verify(args):
    cfg, http, _ = load(args)
    db = open_db(cfg, args)
    r = db.one("SELECT * FROM responses WHERE id=?", (args.id,))
    if not r or r["batch"] is None:
        sys.exit("no such response, or it is not committed yet")
    tok = db.one("SELECT * FROM tokens WHERE mint=?", (r["mint"],))
    b = db.one("SELECT * FROM batches WHERE id=?", (r["batch"],))
    leaf = sha(canon({"mint": r["mint"], "model_id": r["model_id"], "cond": r["cond"],
                      "snapshot_sha": sha(tok["snapshot"]), "prompt_sha": sha(r["messages"]),
                      "response_sha": sha(r["text"]), "created": int(r["created"])}))
    leaves = json.loads(b["leaves"])
    idx = leaves.index(leaf) if leaf in leaves else -1
    print(f"response {r['id']}: {r['model_id']} / condition {r['cond']} / {tok['symbol']} ({r['mint']})")
    print(f"recomputed leaf {leaf} -> {'found' if idx >= 0 else 'NOT FOUND'} in batch {b['id']}")
    if idx < 0:
        sys.exit(1)
    raw = [bytes.fromhex(x) for x in leaves]
    proof = merkle.path(idx, raw)
    ok = merkle.root_from_path(idx, len(raw), raw[idx], proof).hex() == b["root"]
    print(f"Merkle proof ({len(proof)} hashes) reproduces root {b['root']}: {ok}")
    if b["tx"]:
        print(f"anchored in {(cfg.get('anchor') or {}).get('explorer', '')}{b['tx']}")
        try:
            data, block_ts = lookup_tx(http, args.rpc or (cfg.get("anchor") or {}).get("rpc", "https://mainnet.base.org"), b["tx"])
            print(f"calldata matches root: {data == calldata(b['root'])}")
            if block_ts:
                print(f"block time {dt.datetime.fromtimestamp(block_ts, dt.timezone.utc)} UTC, "
                      f"{(tok['t0'] + 21600 - block_ts) / 3600:.2f} h before the 6-hour outcome")
        except Exception as e:
            print("could not read the transaction from the RPC:", e)
    else:
        print("this batch has no transaction yet")


def cmd_export(args):
    cfg, http, _ = load(args)
    db = open_db(cfg, args)
    out = os.path.join(args.dir, "results", "public")
    os.makedirs(out, exist_ok=True)
    for name, sql in (("tokens", "SELECT mint,symbol,name,source,t0,price0,liq0,snapshot,snapshot_sha,card,rugcheck_score FROM tokens"),
                      ("responses", "SELECT id,mint,model,model_id,cond,messages,prompt_sha,text,response_sha,p_collapse_6h,p_halve_6h,p_collapse_24h,action,risk_on,created,leaf,batch FROM responses"),
                      ("outcomes", "SELECT * FROM outcomes"), ("observations", "SELECT * FROM obs"),
                      ("batches", "SELECT * FROM batches"), ("screening", "SELECT * FROM seen")):
        with open(os.path.join(out, name + ".jsonl"), "w") as f:
            for r in db.q(sql):
                d = dict(r)
                # Dual-use: never publish promoter text. Condition P's prompt embeds the
                # project's own description, and a P reply may quote it. Blank the raw
                # messages/text for P rows; keep prompt_sha, response_sha, leaf and the
                # parsed numbers so every aggregate stays reproducible.
                if name == "responses" and d.get("cond") == "P":
                    d["messages"], d["text"] = "", ""
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print("wrote", out, "(condition-P prompts/replies withheld; see the dual-use note in PREREG.md)")


def main():
    ap = argparse.ArgumentParser(prog="rb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".", help="project directory holding config.yaml and .env")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe"); p.add_argument("--minutes", type=int, default=1); p.add_argument("--limit", type=int, default=80); p.set_defaults(fn=cmd_probe)
    p = sub.add_parser("catalog"); p.add_argument("filter", nargs="?", default=""); p.set_defaults(fn=cmd_catalog)
    sub.add_parser("models").set_defaults(fn=cmd_models)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("resolve").set_defaults(fn=cmd_resolve)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    p = sub.add_parser("verify"); p.add_argument("id", type=int); p.add_argument("--rpc", default=""); p.set_defaults(fn=cmd_verify)
    sub.add_parser("export").set_defaults(fn=cmd_export)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
