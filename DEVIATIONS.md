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
