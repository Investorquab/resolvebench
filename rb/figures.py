"""Figures for the report. matplotlib-only (kept out of the frozen requirements and off
the VPS); run on a machine with matplotlib via scripts/make_figures.py against a db copy.

Reads the database read-only. Produces, in out_dir/figures/:
  fig1_stated_vs_actual.png   headline: mean stated P(collapse 6h) per model & condition
                              vs the actual 6h collapse rate
  fig2_calibration.png        reliability diagram per model (condition A)
  fig3_discrimination.png     AUC for 6h collapse: each model (A) vs logistic vs RugCheck
  fig4_pressure_shifts.png    paired change in P(collapse 6h) under B,C,D,D0 vs A, 95% CI
  fig5_flip_rates.png         flip rate under pressure (D) vs neutral re-check (D0)
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .report import auc, boot
from . import analysis as an

INK = "#1b1b1f"
GRID = "#d9d9de"
ACTUAL = "#c1121f"      # actual outcome / reference
MODELC = ["#2a6f97", "#e09f3e", "#6a4c93", "#588157"]  # up to 4 models
CONDS = ["A", "B", "C", "D", "D0"]


def _style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK, labelsize=9)
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def _a_arrays(resp, out, model):
    p, y = [], []
    for m, c in resp[model].items():
        yy = an.collapse6(out, m)
        if "A" in c and c["A"]["p_collapse_6h"] is not None and yy is not None:
            p.append(c["A"]["p_collapse_6h"])
            y.append(yy)
    return np.array(p), np.array(y)


def fig1(out, toks, resp, models, collapse_rate, path):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    _style(ax)
    x = np.arange(len(CONDS))
    w = 0.8 / max(1, len(models))
    for i, model in enumerate(models):
        vals = []
        for cond in CONDS:
            ps = [c[cond]["p_collapse_6h"] for c in resp[model].values()
                  if cond in c and c[cond]["p_collapse_6h"] is not None]
            vals.append(np.mean(ps) if ps else np.nan)
        ax.bar(x + i * w, vals, w, color=MODELC[i % len(MODELC)], label=model, edgecolor="white", lw=0.5)
    ax.axhline(collapse_rate, color=ACTUAL, lw=2, ls="--", label=f"actual 6h collapse rate ({collapse_rate:.0%})")
    ax.set_xticks(x + w * (len(models) - 1) / 2)
    ax.set_xticklabels(CONDS)
    ax.set_ylabel("mean stated P(collapse within 6h)")
    ax.set_ylim(0, 1)
    ax.set_title("Stated collapse probability vs. what actually happened", color=INK, fontsize=12, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig2(out, resp, models, path, bins=10):
    fig, ax = plt.subplots(figsize=(5.2, 5))
    _style(ax)
    ax.plot([0, 1], [0, 1], color=INK, lw=1, ls=":", label="perfect calibration")
    for i, model in enumerate(models):
        p, y = _a_arrays(resp, out, model)
        if len(p) == 0:
            continue
        edges = np.linspace(0, 1, bins + 1)
        idx = np.minimum((p * bins).astype(int), bins - 1)
        xs, ys = [], []
        for b in range(bins):
            if (idx == b).any():
                xs.append(p[idx == b].mean())
                ys.append(y[idx == b].mean())
        ax.plot(xs, ys, "o-", color=MODELC[i % len(MODELC)], lw=1.6, ms=5, label=model)
    ax.set_xlabel("stated P(collapse 6h)")
    ax.set_ylabel("observed collapse frequency")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_title("Reliability diagram, condition A", color=INK, fontsize=12, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig3(out, toks, resp, models, logistic_auc, rugcheck_auc, path):
    labels, aucs, colors = [], [], []
    for i, model in enumerate(models):
        p, y = _a_arrays(resp, out, model)
        a = auc(p, y) if len(set(y)) > 1 else None
        labels.append(model)
        aucs.append(a if a is not None else np.nan)
        colors.append(MODELC[i % len(MODELC)])
    labels += ["logistic\n(card features)", "RugCheck\nscore"]
    aucs += [logistic_auc if logistic_auc is not None else np.nan,
             rugcheck_auc if rugcheck_auc is not None else np.nan]
    colors += ["#344e41", "#9a9a9a"]
    fig, ax = plt.subplots(figsize=(7.2, 4))
    _style(ax)
    xb = np.arange(len(labels))
    ax.bar(xb, aucs, 0.62, color=colors, edgecolor="white")
    ax.axhline(0.5, color=ACTUAL, lw=1.4, ls="--", label="chance (AUC 0.5)")
    for xi, a in zip(xb, aucs):
        if not np.isnan(a):
            ax.text(xi, a + 0.02, f"{a:.2f}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(xb)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("AUC for 6h collapse")
    ax.set_ylim(0, 1)
    ax.set_title("Who can tell which tokens collapse?", color=INK, fontsize=12, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig4(out, resp, models, path):
    conds = ["B", "C", "D", "D0"]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    _style(ax)
    xg = np.arange(len(conds))
    w = 0.8 / max(1, len(models))
    for i, model in enumerate(models):
        means, los, his = [], [], []
        for cond in conds:
            both = [(c["A"]["p_collapse_6h"], c[cond]["p_collapse_6h"]) for c in resp[model].values()
                    if "A" in c and cond in c and c["A"]["p_collapse_6h"] is not None and c[cond]["p_collapse_6h"] is not None]
            d = [b - a for a, b in both]
            b = boot(d)
            means.append(b["mean"] if b else np.nan)
            los.append((b["mean"] - b["lo"]) if b else 0)
            his.append((b["hi"] - b["mean"]) if b else 0)
        ax.bar(xg + i * w, means, w, yerr=[los, his], capsize=3, color=MODELC[i % len(MODELC)],
               edgecolor="white", label=model, error_kw={"lw": 1, "ecolor": INK})
    ax.axhline(0, color=INK, lw=1)
    ax.set_xticks(xg + w * (len(models) - 1) / 2)
    ax.set_xticklabels(["B hype", "C sunk cost", "D pushback", "D0 re-check (control)"], fontsize=9)
    ax.set_ylabel("change in P(collapse 6h) vs. A")
    ax.set_title("How social pressure moves the stated probability", color=INK, fontsize=12, loc="left")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig5(out, resp, models, path):
    fig, ax = plt.subplots(figsize=(6.8, 4))
    _style(ax)
    xg = np.arange(len(models))
    w = 0.38
    dvals, d0vals = [], []
    for model in models:
        d, d0 = [], []
        for c in resp[model].values():
            a = c.get("A")
            if not a or a["risk_on"] is None:
                continue
            start = a["risk_on"]
            fd, f0 = c.get("D", {}).get("risk_on"), c.get("D0", {}).get("risk_on")
            if fd is not None:
                d.append(int(fd != start))
            if f0 is not None:
                d0.append(int(f0 != start))
        dvals.append(np.mean(d) if d else 0)
        d0vals.append(np.mean(d0) if d0 else 0)
    ax.bar(xg - w / 2, dvals, w, color=ACTUAL, label="pressure (D)", edgecolor="white")
    ax.bar(xg + w / 2, d0vals, w, color="#9a9a9a", label="neutral re-check (D0)", edgecolor="white")
    ax.set_xticks(xg)
    ax.set_xticklabels(models, fontsize=9)
    ax.set_ylabel("share of advice that flips")
    ax.set_ylim(0, max(0.05, max(dvals + d0vals) * 1.3))
    ax.set_title("Does the advice flip under pressure?", color=INK, fontsize=12, loc="left")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def make_all(db, out_dir="results"):
    fdir = os.path.join(out_dir, "figures")
    os.makedirs(fdir, exist_ok=True)
    out, toks, resp = an.load(db)
    models = sorted(resp, key=lambda m: -an.confirmatory_models(out, resp)[1][m])
    # 6h collapse rate
    c6 = [o["6h"]["collapse"] for o in out.values() if "6h" in o]
    rate = float(np.mean(c6)) if c6 else 0.0
    lb = an.logistic_baseline(toks, out)
    rc = [(t["rugcheck_score"], an.collapse6(out, m)) for m, t in toks.items()
          if t.get("rugcheck_score") is not None and an.collapse6(out, m) is not None]
    rc_auc = auc(*zip(*rc)) if len(rc) >= 5 and len(set(x[1] for x in rc)) > 1 else None
    fig1(out, toks, resp, models, rate, os.path.join(fdir, "fig1_stated_vs_actual.png"))
    fig2(out, resp, models, os.path.join(fdir, "fig2_calibration.png"))
    fig3(out, toks, resp, models, lb.get("auc"), rc_auc, os.path.join(fdir, "fig3_discrimination.png"))
    fig4(out, resp, models, os.path.join(fdir, "fig4_pressure_shifts.png"))
    fig5(out, resp, models, os.path.join(fdir, "fig5_flip_rates.png"))
    return fdir
