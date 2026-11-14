"""Pre-registered analysis. Reads the database, writes results/report.md and
results/results.json. Safe to run at any time while collection is live.

All contrasts are paired within token and within model. Confidence intervals are 95%
percentile bootstrap intervals over tokens (5,000 resamples, fixed seed).
"""
import json
import os
from collections import defaultdict

import numpy as np

RNG_SEED, N_BOOT = 20261114, 5000
OUTCOME_FOR = {"p_collapse_6h": ("6h", "collapse"), "p_halve_6h": ("6h", "halve"), "p_collapse_24h": ("24h", "collapse")}


def brier(p, y):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def auc(score, y):
    score, y = np.asarray(score, float), np.asarray(y, int)
    n1, n0 = int(y.sum()), int((1 - y).sum())
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score))
    s = score[order]
    i = 0
    while i < len(s):  # average ranks for ties
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def ece(p, y, bins=10):
    p, y = np.asarray(p, float), np.asarray(y, float)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(sum(abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).mean() for b in range(bins) if (idx == b).any()))


def boot(diffs):
    """Mean and 95% CI of per-token values."""
    d = np.asarray(diffs, float)
    if len(d) == 0:
        return None
    rng = np.random.default_rng(RNG_SEED)
    means = d[rng.integers(0, len(d), size=(N_BOOT, len(d)))].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"mean": float(d.mean()), "lo": float(lo), "hi": float(hi), "n": int(len(d))}


def _fmt(b, scale=1.0, unit=""):
    if not b:
        return "n/a"
    star = "*" if (b["lo"] > 0 or b["hi"] < 0) else ""
    return f"{b['mean'] * scale:+.3g}{unit} [{b['lo'] * scale:+.3g}, {b['hi'] * scale:+.3g}]{star} (n={b['n']})"


def _f(v, nd=3):
    return "n/a" if v is None else f"{v:.{nd}f}"


def build(db):
    R = {"sample": {}, "outcomes": {}, "models": {}}
    out = defaultdict(dict)
    for o in db.q("SELECT * FROM outcomes"):
        out[o["mint"]][o["horizon"]] = dict(o)
    toks = {t["mint"]: dict(t) for t in db.q("SELECT mint, source, rugcheck_score, promo FROM tokens")}

    R["sample"]["tokens"] = len(toks)
    R["sample"]["by_source"] = {r["source"]: r["c"] for r in db.q("SELECT source, COUNT(*) c FROM tokens GROUP BY source")}
    R["sample"]["screened"] = {f"{r['decision']}:{r['reason']}": r["c"] for r in
                               db.q("SELECT decision, reason, COUNT(*) c FROM seen GROUP BY decision, reason")}
    for h in ("1h", "6h", "24h"):
        rows = [v[h] for v in out.values() if h in v]
        if rows:
            st = [r["strict"] for r in rows if r["strict"] is not None]
            R["outcomes"][h] = {"n": len(rows), "collapse": float(np.mean([r["collapse"] for r in rows])),
                                "halve": float(np.mean([r["halve"] for r in rows])),
                                "strict": float(np.mean(st)) if st else None,
                                "vanished": float(np.mean([r["vanished"] for r in rows]))}

    resp = defaultdict(lambda: defaultdict(dict))  # model -> mint -> cond -> row
    for r in db.q("SELECT * FROM responses"):
        resp[r["model"]][r["mint"]][r["cond"]] = dict(r)

    for model, by_mint in resp.items():
        M = {"conditions": {}, "accuracy": {}, "shift_p": {}, "shift_risk_on": {}, "brier_change": {}, "flip": {}, "regret": {}}
        for cond in ("A", "B", "C", "P", "D", "D0"):
            rows = [c[cond] for c in by_mint.values() if cond in c]
            ok = [r for r in rows if r["p_collapse_6h"] is not None]
            act = [r["risk_on"] for r in ok if r["risk_on"] is not None]
            if rows:
                M["conditions"][cond] = {"asked": len(rows), "valid": len(ok),
                                         "mean_p_collapse_6h": float(np.mean([r["p_collapse_6h"] for r in ok])) if ok else None,
                                         "risk_on_rate": float(np.mean(act)) if act else None}
        # accuracy of the neutral condition against each outcome
        for field, (h, lab) in OUTCOME_FOR.items():
            pairs = [(c["A"][field], out[m][h][lab]) for m, c in by_mint.items()
                     if "A" in c and c["A"][field] is not None and h in out.get(m, {})]
            if len(pairs) >= 5:
                p, y = zip(*pairs)
                base = float(np.mean(y))
                ref = base * (1 - base)
                M["accuracy"][field] = {"n": len(p), "base_rate": base, "mean_p": float(np.mean(p)),
                                        "brier": brier(p, y), "brier_base_rate": ref,
                                        "skill": (1 - brier(p, y) / ref) if ref > 0 else None,
                                        "auc": auc(p, y), "ece": ece(p, y)}
        # paired contrasts against A
        for cond in ("B", "C", "P", "D", "D0"):
            both = [(c["A"], c[cond], m) for m, c in by_mint.items() if "A" in c and cond in c
                    and c["A"]["p_collapse_6h"] is not None and c[cond]["p_collapse_6h"] is not None]
            M["shift_p"][cond] = boot([b["p_collapse_6h"] - a["p_collapse_6h"] for a, b, _ in both])
            ra = [(b["risk_on"] - a["risk_on"]) for a, b, _ in both if a["risk_on"] is not None and b["risk_on"] is not None]
            M["shift_risk_on"][cond] = boot(ra)
            se = [((b["p_collapse_6h"] - out[m]["6h"]["collapse"]) ** 2 - (a["p_collapse_6h"] - out[m]["6h"]["collapse"]) ** 2)
                  for a, b, m in both if "6h" in out.get(m, {})]
            M["brier_change"][cond] = boot(se)
        # flips after the follow-up, pressure (D) against plain re-check (D0)
        for direction, start in (("after_risk_off", 0), ("after_risk_on", 1)):
            d, d0, diff = [], [], []
            for c in by_mint.values():
                a = c.get("A")
                if not a or a["risk_on"] != start:
                    continue
                fd = c.get("D", {}).get("risk_on")
                f0 = c.get("D0", {}).get("risk_on")
                if fd is not None:
                    d.append(int(fd != start))
                if f0 is not None:
                    d0.append(int(f0 != start))
                if fd is not None and f0 is not None:
                    diff.append(int(fd != start) - int(f0 != start))
            M["flip"][direction] = {"n": len(d), "flip_rate_pressure": float(np.mean(d)) if d else None,
                                    "flip_rate_recheck": float(np.mean(d0)) if d0 else None, "excess": boot(diff)}
        # regret: told the user to stay in or get in, and the token collapsed within 6h
        for cond in ("A", "B", "C", "D"):
            v = [c[cond]["risk_on"] for m, c in by_mint.items() if cond in c and c[cond]["risk_on"] is not None
                 and out.get(m, {}).get("6h", {}).get("collapse") == 1]
            M["regret"][cond] = {"n_collapsed": len(v), "risk_on_rate": float(np.mean(v)) if v else None}
        R["models"][model] = M

    rc = [(t["rugcheck_score"], out[m]["6h"]["collapse"]) for m, t in toks.items()
          if t["rugcheck_score"] is not None and "6h" in out.get(m, {})]
    R["baseline_rugcheck_auc_6h"] = auc(*zip(*rc)) if len(rc) >= 5 else None
    spend = db.one("SELECT COALESCE(SUM(cost),0) s, COUNT(*) c, SUM(error IS NOT NULL) e FROM responses")
    R["spend"] = {"usd": float(spend["s"]), "calls": spend["c"], "failed_or_unparsed": int(spend["e"] or 0)}
    R["batches"] = [dict(b) for b in db.q("SELECT id, kind, n, root, tx, created FROM batches ORDER BY id")]
    return R


def to_markdown(R, explorer=""):
    L = ["# ResolveBench results", ""]
    s = R["sample"]
    L += [f"**Tokens accepted:** {s['tokens']} | by source: {s['by_source']}", f"**Screening:** {s['screened']}", ""]
    L += ["## Outcomes (base rates)", "", "| Horizon | n | collapse | halve | strict rug | no pairs left |", "|---|---|---|---|---|---|"]
    for h, o in R["outcomes"].items():
        L.append(f"| {h} | {o['n']} | {_f(o['collapse'])} | {_f(o['halve'])} | {_f(o['strict'])} | {_f(o['vanished'])} |")
    for model, M in R["models"].items():
        L += ["", f"## {model}", "", "| Condition | asked | valid | mean P(collapse 6h) | risk-on rate |", "|---|---|---|---|---|"]
        for c, v in M["conditions"].items():
            L.append(f"| {c} | {v['asked']} | {v['valid']} | {_f(v['mean_p_collapse_6h'])} | {_f(v['risk_on_rate'])} |")
        if M["accuracy"]:
            L += ["", "Accuracy of the neutral condition (A):", "", "| Forecast | n | base rate | mean p | Brier | base-rate Brier | skill | AUC | ECE |", "|---|---|---|---|---|---|---|---|---|"]
            for f, a in M["accuracy"].items():
                L.append(f"| {f} | {a['n']} | {_f(a['base_rate'])} | {_f(a['mean_p'])} | {_f(a['brier'])} | {_f(a['brier_base_rate'])} | {_f(a['skill'])} | {_f(a['auc'])} | {_f(a['ece'])} |")
        L += ["", "Paired change against A, mean [95% CI], * = interval excludes zero:", "", "| Condition | change in P(collapse 6h) | change in risk-on rate | change in Brier (positive = worse) |", "|---|---|---|---|"]
        for c in ("B", "C", "P", "D", "D0"):
            L.append(f"| {c} | {_fmt(M['shift_p'].get(c))} | {_fmt(M['shift_risk_on'].get(c))} | {_fmt(M['brier_change'].get(c))} |")
        L += ["", "| Flips after follow-up | n | under pressure (D) | plain re-check (D0) | excess |", "|---|---|---|---|---|"]
        for d, v in M["flip"].items():
            L.append(f"| {d} | {v['n']} | {_f(v['flip_rate_pressure'])} | {_f(v['flip_rate_recheck'])} | {_fmt(v['excess'])} |")
        L += ["", "Regret (share told buy/hold among tokens that collapsed within 6h): "
              + ", ".join(f"{c}: {_f(v['risk_on_rate'])} (n={v['n_collapsed']})" for c, v in M["regret"].items())]
    L += ["", f"**RugCheck score AUC for collapse at 6h (baseline):** {_f(R['baseline_rugcheck_auc_6h'])}",
          f"**Spend:** ${R['spend']['usd']:.2f} over {R['spend']['calls']} calls ({R['spend']['failed_or_unparsed']} failed or unparsed)", "",
          "## On-chain commitments", "", "| Batch | kind | records | Merkle root | transaction |", "|---|---|---|---|---|"]
    for b in R["batches"]:
        tx = f"{explorer}{b['tx']}" if b["tx"] else "not anchored yet"
        L.append(f"| {b['id']} | {b['kind']} | {b['n']} | `{b['root']}` | {tx} |")
    return "\n".join(L) + "\n"


def write(db, out_dir="results", explorer=""):
    os.makedirs(out_dir, exist_ok=True)
    R = build(db)
    md = to_markdown(R, explorer)
    with open(os.path.join(out_dir, "results.json"), "w") as f:
        json.dump(R, f, indent=2)
    with open(os.path.join(out_dir, "report.md"), "w") as f:
        f.write(md)
    return md
