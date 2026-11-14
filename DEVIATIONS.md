# Deviations from the pre-registration

The pre-registration (`PREREG.md`), `config.yaml` and `rb/prompts.py` were hashed and
anchored on Base Sepolia at **2026-11-14 22:23:25 UTC** (prereg batch, tx
`0xbf3a0eddff127bbb3bd5020fe271477c96574bfc6f8652890a5c9dfbefedb6dc`). Those three files
are unchanged. This file records every change to the stated procedure made after that
moment, as required by the pre-registration.

## 1. Inclusion filter re-evaluated on every poll (not only at first sighting)

- **When:** 2026-11-14 ~22:58 UTC, ~35 minutes into collection. Made **before any 6-hour
  outcome existed** (the earliest outcome is ~04:23 UTC on 2026-11-15), so no outcome
  information could have influenced it.
- **What the pre-registration said:** "Inclusion, applied once at first sighting ...
  Tokens younger than 5 minutes are looked at again on the next poll." I.e. a token
  rejected at first sighting (for example for low liquidity) was never reconsidered.
- **What changed:** the inclusion filter is now applied on **every** poll a candidate
  appears in, not only the first. A token first seen below the liquidity threshold is
  re-evaluated on later polls and included at the moment it crosses the threshold, while
  still within the 5-minute-to-24-hour age window. Already-accepted tokens are never
  re-added; tokens that have aged out are not reconsidered. Implemented in
  `rb/run.py` (`Runner._recheckable`); no change to any frozen file.
- **Why:** in the first ~35 minutes, intake after the initial backlog was ~2.6 new
  tokens/hour, because most newly launched tokens surface in the source feeds while
  still below the $10,000 liquidity threshold, were rejected once, and were then
  permanently excluded — even if their liquidity grew past the threshold minutes later.
  At that rate the study would have finished with ~30 tokens, below the pre-registered
  minimum of 50 tokens per model (with a valid A response and a 6-hour outcome) needed
  to keep a model in the confirmatory tests.
- **Effect on comparability:** the **$10,000 liquidity definition of "accepted" is
  unchanged**, so every accepted token still meets the same inclusion bar and remains
  directly comparable. Only the *timing* of eligibility changes (any qualifying poll,
  not just the first). This already matched the pre-registered treatment of
  "too-new" tokens, which were always re-checked on later polls.
- **Known limitation introduced:** tokens that start below the threshold and grow into
  it are accepted at a later age than tokens that qualified immediately, which can
  mildly over-represent tokens whose liquidity rose after launch. Source is recorded per
  token, and `t0`/age are in each snapshot, so this is measurable and reported.

## 2. Minimum liquidity threshold lowered from $10,000 to $5,000

- **When:** 2026-11-14 ~23:16 UTC, ~53 minutes into collection. Made **before any
  6-hour outcome existed** (earliest outcome ~04:23 UTC on 2026-11-15), so no outcome
  information could have influenced it.
- **What the pre-registration said:** "summed pool liquidity of at least $10,000"
  (`PREREG.md`; `config.yaml` `filters.min_liquidity_usd: 10000`).
- **What changed:** `config.yaml` `filters.min_liquidity_usd` set to `5000`. `PREREG.md`
  is left unchanged and still states $10,000; this file is the record of the difference.
- **Why:** even after deviation 1, intake was ~4 new tokens/hour, projecting ~40 tokens
  by the 06:00 UTC stop — below the pre-registered minimum of 50 tokens per model (with a
  valid A response and a 6-hour outcome) required to keep a model in the confirmatory
  tests, which include the outcome-based results (calibration, whether moving under
  pressure was warranted, regret) that are the central contribution.
- **Effect on the on-chain commitment:** the SHA-256 of `config.yaml` changed from
  `7693b3deb89871235432d916961175d3867ad1a543fbc96e962de853aeb693e1` (the value in the
  prereg Merkle leaf anchored on Base Sepolia at 22:23:25 UTC, tx
  `0xbf3a0eddff127bbb3bd5020fe271477c96574bfc6f8652890a5c9dfbefedb6dc`) to
  `3baf59b1eb96fcdfcd0f7f55a7ded9660717ccda128981586290530f44672507`. The **original
  hash remains anchored on-chain and is the pre-registered commitment**; the repository
  now carries the amended `config.yaml`. The anchoring of model **responses** before
  their outcomes — the core integrity mechanism — is unchanged.
- **Effect on analysis:** tokens accepted before ~23:16 UTC have ≥$10,000 liquidity;
  those after have ≥$5,000. All confirmatory contrasts are paired within token, so the
  shift and flip tests (H2, H3, H4) are unaffected. Base-rate, calibration and
  outcome-based analyses pool a mildly heterogeneous sample; liquidity is recorded per
  token (`liq0`), the results are reported with this caveat, and the key analyses can be
  re-run on the ≥$10,000 subset as a robustness check. Lower-liquidity tokens may raise
  the collapse base rate, which is reported.
