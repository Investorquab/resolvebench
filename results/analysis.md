# ResolveBench — inferential & exploratory analysis

**Min-n gate:** 50 tokens with a valid A response and a 6h outcome.
**Confirmatory models:** gemini-free, groq-open.
**Valid-A & 6h per model:** {'groq-open': 60, 'gemini-free': 64, 'groq-open-2': 45}

## Confirmatory contrasts (effect [95% CI]; p = sign-flip permutation; Holm across confirmatory models)

### H1_brier_skill_A
*mean>0 and p<.05 => A is better calibrated than guessing the base rate (rejects H1's null of no skill)*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | -0.178 [-0.277, -0.0733] | 64 | 0.00075 | 0.0015 | **yes** | yes |
| groq-open | -0.161 [-0.253, -0.0618] | 60 | 0.00245 | 0.00245 | **yes** | yes |
| groq-open-2 | -0.107 [-0.198, -0.0194] | 45 | 0.0223 | n/a | no | no (min-n) |

### H2_hype_dP
*mean<0 => B lowers stated P(collapse 6h) vs A*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | +0.0589 [+0.0391, +0.0792] | 64 | 0 | 0 | **yes** | yes |
| groq-open | +0.0113 [-0.0169, +0.0392] | 52 | 0.447 | 0.447 | no | yes |
| groq-open-2 | +0.0533 [-0.0256, +0.131] | 45 | 0.196 | n/a | no | no (min-n) |

### H2_hype_dRiskOn
*mean>0 => B raises the risk-on rate vs A*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | -0.0156 [-0.0469, +0] | 64 | 1 | 1 | no | yes |
| groq-open | +0 [+0, +0] | 52 | 1 | 1 | no | yes |
| groq-open-2 | +0 [+0, +0] | 45 | 1 | n/a | no | no (min-n) |

### H3_sunkcost_dP
*mean<0 => C lowers stated P(collapse 6h) vs A*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | -0.0453 [-0.0672, -0.0242] | 64 | 0.0003 | 0.0003 | **yes** | yes |
| groq-open | -0.105 [-0.142, -0.0694] | 49 | 0 | 0 | **yes** | yes |
| groq-open-2 | -0.0789 [-0.153, -0.00111] | 45 | 0.0605 | n/a | no | no (min-n) |

### H3_sunkcost_dRiskOn
*mean>0 => C raises the risk-on rate vs A*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | +0.0156 [-0.0312, +0.0625] | 64 | 1 | 1 | no | yes |
| groq-open | +0 [+0, +0] | 49 | 1 | 1 | no | yes |
| groq-open-2 | +0 [+0, +0] | 45 | 1 | n/a | no | no (min-n) |

### H4_flip_excess_after_risk_on
*mean>0 => pressure (D) flips the advice more than a neutral re-check (D0)*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | +0 [+0, +0] | 1 | 1 | 1 | no | yes |
| groq-open | n/a | 0 | n/a | n/a | no | yes |
| groq-open-2 | n/a | 0 | n/a | n/a | no | no (min-n) |

### H4_flip_excess_after_risk_off
*mean>0 => pressure (D) flips the advice more than a neutral re-check (D0)*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | +0 [+0, +0] | 63 | 1 | 1 | no | yes |
| groq-open | +0 [+0, +0] | 45 | 1 | 1 | no | yes |
| groq-open-2 | +0 [+0, +0] | 45 | 1 | n/a | no | no (min-n) |

### H5_brier_worse_B
*mean>0 => when B moves the probability, it moves away from the truth*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | +0.11 [+0.0641, +0.156] | 34 | 0.00025 | 0.0005 | **yes** | yes |
| groq-open | +0.0251 [-0.0135, +0.0622] | 46 | 0.224 | 0.224 | no | yes |
| groq-open-2 | +0.00303 [-0.114, +0.118] | 33 | 0.965 | n/a | no | no (min-n) |

### H5_brier_worse_C
*mean>0 => when C moves the probability, it moves away from the truth*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | -0.0432 [-0.0865, -0.00154] | 39 | 0.055 | 0.055 | no | yes |
| groq-open | -0.0827 [-0.135, -0.0297] | 43 | 0.00335 | 0.0067 | **yes** | yes |
| groq-open-2 | -0.0417 [-0.162, +0.0843] | 33 | 0.512 | n/a | no | no (min-n) |

### H5_brier_worse_D
*mean>0 => when D moves the probability, it moves away from the truth*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | -0.0419 [-0.0597, -0.0208] | 18 | 0.00221 | 0.00443 | **yes** | yes |
| groq-open | +0.00401 [-0.0041, +0.0119] | 48 | 0.336 | 0.336 | no | yes |
| groq-open-2 | n/a | 0 | n/a | n/a | no | no (min-n) |

### H6_regret_B
*mean>0 => among tokens that collapsed, B tells more users to buy/hold than A*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | +0 [+0, +0] | 20 | 1 | 1 | no | yes |
| groq-open | +0 [+0, +0] | 16 | 1 | 1 | no | yes |
| groq-open-2 | +0 [+0, +0] | 18 | 1 | n/a | no | no (min-n) |

### H6_regret_C
*mean>0 => among tokens that collapsed, C tells more users to buy/hold than A*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | +0 [+0, +0] | 20 | 1 | 1 | no | yes |
| groq-open | +0 [+0, +0] | 15 | 1 | 1 | no | yes |
| groq-open-2 | +0 [+0, +0] | 18 | 1 | n/a | no | no (min-n) |

### H6_regret_D
*mean>0 => among tokens that collapsed, D tells more users to buy/hold than A*

| model | effect mean [95% CI] | n | p (raw) | p (Holm) | reject @.05 | confirmatory |
|---|---|---|---|---|---|---|
| gemini-free | +0 [+0, +0] | 20 | 1 | 1 | no | yes |
| groq-open | +0 [+0, +0] | 14 | 1 | 1 | no | yes |
| groq-open-2 | +0 [+0, +0] | 18 | 1 | n/a | no | no (min-n) |

## Baseline: logistic regression on card features (6h collapse)

- n=64, 5 features (liquidity_usd, top10_pct, insider_wallets, volume_h6, age_minutes)
- 5-fold, L2=1.0, out-of-fold; AUC 95% bootstrap over tokens (2000 resamples); base rate 0.312
- Brier 0.218 (base-rate Brier 0.215; skill -0.013)
- AUC 0.649 [0.515, 0.781], ECE 0.184

## Base rate and A-calibration by source

| source | tokens | n(6h) | collapse 6h | A mean p | A Brier | A AUC | A n |
|---|---|---|---|---|---|---|---|
| dexscreener_boosts | 7 | 7 | 0.000 | 0.661 | 0.461 | n/a | 17 |
| dexscreener_profiles | 53 | 53 | 0.340 | 0.695 | 0.370 | 0.483 | 140 |
| geckoterminal_new_pools | 4 | 4 | 0.500 | 0.787 | 0.311 | 0.639 | 12 |

## Exploratory #2 — advice that contradicts its own number

Share of **risk-on** answers that nonetheless state P(collapse 6h) >= 0.5:

| model | A | B | C | D | D0 |
|---|---|---|---|---|---|
| groq-open | n/a | n/a | n/a | n/a | n/a |
| gemini-free | 1.00 (n=1) | n/a | 0.50 (n=2) | n/a | n/a |
| groq-open-2 | n/a | n/a | n/a | n/a | n/a |

## Exploratory #3 — binary accuracy vs a proper score

- Rank by accuracy of the buy/avoid call: ['groq-open-2', 'gemini-free', 'groq-open']
- Rank by Brier: ['groq-open-2', 'groq-open', 'gemini-free']
- Rankings agree: False
- 'Always avoid' strategy: accuracy 0.337 (= base rate); Brier if it forecast p=1 always: 0.663

| model | n(action) | accuracy buy/avoid | n(prob) | Brier |
|---|---|---|---|---|
| groq-open | 60 | 0.317 | 60 | 0.377 |
| gemini-free | 64 | 0.328 | 64 | 0.392 |
| groq-open-2 | 45 | 0.400 | 45 | 0.347 |

## Exploratory #4 — does within-token inconsistency predict A's error?

Frame spread = max - min of P(collapse 6h) over A,B,C; correlated (Spearman) with A's squared error.

| model | n | Spearman rho | 95% CI |
|---|---|---|---|
| groq-open | 47 | +0.059 | [-0.226, +0.336] |
| gemini-free | 64 | -0.264 | [-0.498, -0.011] |
| groq-open-2 | 45 | +0.177 | [-0.166, +0.504] |

## Exploratory #1 — implication gap (stated number - judged implied, from prose)

*positive gap = prose sounds safer than the stated number (overselling); negative = prose sounds more alarmed. Validation vs 40 human labels pending.*

- Responses judged: 491 (765 verdicts, two cross-family judges each)
- **Overall gap:** -0.163 [-0.178, -0.148] (n=491)
- Judge agreement: Pearson 0.4863097220821447, Spearman 0.4399368394626536, mean |diff| 0.06653284671532846 (n_pairs=274)

| condition | gap mean [95% CI] |
|---|---|
| A | -0.153 [-0.176, -0.130] (n=169) |
| B | -0.139 [-0.161, -0.119] (n=162) |
| C | -0.199 [-0.229, -0.167] (n=160) |

| author model | gap mean [95% CI] |
|---|---|
| gemini-free | -0.064 [-0.083, -0.045] (n=192) |
| groq-open | -0.186 [-0.202, -0.171] (n=164) |
| groq-open-2 | -0.276 [-0.307, -0.245] (n=135) |
