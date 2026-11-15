"""Pairwise Spearman agreement among the AI judges on the 40-item implication-gap set.

Judges:
  - gemini-3.5-flash-lite (gemini-free), gpt-oss-120b (groq-open), qwen3 (groq-open-2)
    read from data/implied.sqlite (cross-family design: each item judged by the two
    families that did NOT author it, so each covers only a subset of the 40 items).
  - claude-fable-5-2 read from third_ai_judge_claude_labels.csv (all 40 items).

Agreement between AI judges is NOT validity: convergence does not establish that any
judge tracks what a human reader would infer. No human labels are used anywhere.

Usage: python scripts/judge_agreement.py
"""
import csv
import json
import sqlite3
import sys
from itertools import combinations

import numpy as np


def rankdata(a):
    a = np.asarray(a, float)
    order = a.argsort()
    ranks = np.empty(len(a), float)
    ranks[order] = np.arange(1, len(a) + 1)
    # average ties
    _, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    return (sums / counts)[inv]


def spearman(x, y):
    if len(x) < 3:
        return None
    rx, ry = rankdata(x), rankdata(y)
    rx, ry = rx - rx.mean(), ry - ry.mean()
    denom = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / denom) if denom else None


def main(root="."):
    key = json.load(open(f"{root}/results/validation/label_key.json"))
    refs = [r["resp_id"] for r in key]

    judges = {}  # judge_name -> {resp_id: p}

    con = sqlite3.connect(f"{root}/data/implied.sqlite")
    q = "select resp_id, judge, implied_p, ok from implied where resp_id in (%s)" % ",".join("?" * len(refs))
    for rid, judge, p, ok in con.execute(q, refs):
        if ok and p is not None:
            judges.setdefault(judge, {})[rid] = float(p)

    csv_path = f"{root}/results/validation/third_ai_judge_claude_labels.csv"
    if not __import__("os").path.exists(csv_path):  # fallback to repo root
        csv_path = f"{root}/third_ai_judge_claude_labels.csv"
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            judges.setdefault("claude-fable-5-2", {})[int(row["ref"])] = float(row["p_implied_collapse_6h"])

    print("coverage of the 40 items:")
    for j, d in sorted(judges.items()):
        print(f"  {j}: {len(d)}")

    print("\npairwise Spearman (n = items both judged):")
    names = sorted(judges)
    lines = ["| judge A | judge B | Spearman | n |", "|---|---|---|---|"]
    for a, b in combinations(names, 2):
        common = sorted(set(judges[a]) & set(judges[b]))
        xa = [judges[a][r] for r in common]
        xb = [judges[b][r] for r in common]
        rho = spearman(xa, xb)
        flag = "" if len(common) >= 10 else "  (n<10: not interpretable)"
        rho_s = f"{rho:+.3f}" if rho is not None else "n/a"
        print(f"  {a} vs {b}: rho={rho_s}, n={len(common)}{flag}")
        lines.append(f"| {a} | {b} | {rho_s} | {len(common)} |")

    out = f"{root}/results/validation/judge_agreement.md"
    with open(out, "w") as f:
        f.write("# Pairwise Spearman agreement among AI judges (40-item set)\n\n")
        f.write("Agreement between AI judges is **not** validity; no human labels are used.\n\n")
        f.write("\n".join(lines) + "\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
