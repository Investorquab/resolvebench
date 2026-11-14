# Deviations from the pre-registration

`PREREG.md`, `config.yaml` and `rb/prompts.py` were hashed and anchored on Base Sepolia
(chain 84532) in the **prereg** batch at **2026-11-14T22:23:25Z**, transaction
`0xbf3a0eddff127bbb3bd5020fe271477c96574bfc6f8652890a5c9dfbefedb6dc`, with leaves:

| File | SHA-256 anchored in prereg |
|---|---|
| `PREREG.md` | `07ed5ed288ee45bae6b598be2827c162d60218b698f6966ff9624b66ce567075` |
| `config.yaml` (original) | `7693b3deb89871235432d916961175d3867ad1a543fbc96e962de853aeb693e1` |
| `rb/prompts.py` | `785dcc5ba2db3770fe4b274e2389dc0d6265d395efca05f021ac52d33b907ae4` |

**`PREREG.md` has not been edited and remains as anchored.** `rb/prompts.py` (the frozen
response parser and condition wording) has not been edited. This file records every change
to the procedure made after the run started (2026-11-14T22:23:24Z, from `data/run.log`).
Timestamps are taken from `data/run.log` (when a change took effect, i.e. the service
restart that loaded it) and from `git log` (when it was committed), not from memory. The
amended `config.yaml` and this file are themselves anchored on-chain in a later
**amendment** batch (see the end of this file).

## (a) `filters.min_liquidity_usd` lowered from 10000 to 5000

- **Took effect:** 2026-11-14T23:17:05Z (runner restart banner in `data/run.log`).
  **Committed:** 2026-11-14T23:18:28Z (git `81660cf`).
- **Pre-registered value:** $10,000 (`PREREG.md`: "summed pool liquidity of at least
  $10,000"; `config.yaml` `filters.min_liquidity_usd: 10000`).
- **Change:** `config.yaml` `filters.min_liquidity_usd` set to `5000`. No other filter
  value changed. `PREREG.md` is unchanged and still states $10,000.
- **Reason:** under the pre-registered $10,000 rule, intake after the initial backlog was
  about **4 eligible tokens per hour** (even after change (b)), which projected to ~40
  tokens by the 06:00Z stop — below the pre-registered minimum of 50 tokens per model
  (with a valid A response and a 6-hour outcome) needed to keep a model in the
  confirmatory tests.
- **Effect on the commitment:** the SHA-256 of `config.yaml` changed from the anchored
  `7693b3de…693e1` to a new value anchored in the amendment batch below. The original hash
  remains the pre-registered commitment on-chain. Response anchoring is unchanged.
- **Effect on analysis:** tokens with `t0` before 23:17:05Z have `liq0` ≥ $10,000; later
  tokens have `liq0` ≥ $5,000 (`liq0` is stored per token). Per instruction, every
  confirmatory result will be reported twice — on the full sample and on the
  `liq0 ≥ $10,000` subset (the pre-registered rule) — and the collapse base rate will be
  reported separately for the $5,000–$10,000 band. Paired contrasts (H2, H3, H4) are
  within-token and unaffected.

## (b) Re-check logic: inclusion filter applied on every poll, not only at first sighting

- **Took effect:** 2026-11-14T22:58:24Z (runner restart banner in `data/run.log`).
  **Committed:** 2026-11-14T23:04:07Z (git `c539f3d`). Code: `Runner._recheckable` in
  `rb/run.py`.
- **Pre-registered behaviour:** "Inclusion, applied once at first sighting." A token
  rejected on first sighting was recorded in the `seen` table and never reconsidered
  (except tokens younger than 5 minutes, which were already re-checked next poll because
  they are not written to `seen`).
- **What it now does, exactly:** on every 3-minute discovery poll, each candidate returned
  by the source feeds is screened against the current inclusion filter. A candidate is
  re-screened if it has never been seen, **or** if its `seen` row is a rejection whose
  reason is anything other than `too_old`. The rejection reasons it therefore re-checks
  are: `low_liquidity`, `no_priced_pair`, `no_age`, `inactive`, and `hourly_cap`. It does
  **not** re-check `too_old` (age only increases) and never re-adds a token already
  recorded as `accepted`. When a re-screened token passes the filter it is accepted at
  that poll, its `seen` row is updated to `accepted`, and T0 is the acceptance time. The
  $10,000 (later $5,000) liquidity bar itself was unchanged by this item; only the timing
  of eligibility changed. This generalises the behaviour the pre-registration already
  specified for "too-new" tokens.
- **Reason:** most newly launched tokens appear in the feeds while still below the
  liquidity bar, were rejected once, and were then permanently excluded even if their
  liquidity later grew past the bar. Intake after the startup backlog was ~2.6 tokens/hour.

## (c) Tokens accepted before the changes, and outcome existence at the time

Queried from the database, not estimated:

- **Tokens accepted before change (a):** **14** (tokens with `t0` before 2026-11-14
  23:17:00Z). Change (b) took effect earlier, at 22:58:24Z, by which point **13** tokens
  had been accepted (11 in the startup backlog at 22:23:26Z, then 1 at 22:41:30Z and 1 at
  22:47:31Z).
- **Outcomes at the moment of either change:** **none.** The `outcomes` table had 0 rows,
  and the earliest possible 6-hour outcome is 2026-11-15T04:23:25Z (the first token's
  `t0` of 2026-11-14T22:23:25Z plus 6 hours) — about 5 hours after change (a) and 5.5
  hours after change (b). No outcome information existed when either change was made, so
  neither change could have been influenced by an outcome.

## (d) Other code changes since setup that could affect acceptance or parsing

- **`rb/models.py` — tolerate list-shaped error bodies.** Made during setup **before the
  run started** (part of the initial import, git commit 2026-11-14T22:43:14Z). Google's
  OpenAI-compatible endpoint returns errors as a JSON list (`[{"error": …}]`) rather than
  an object; the client now coerces that to an error instead of crashing. This changes
  only how failed API calls are handled; it does **not** change how a valid response is
  parsed (the parser, `rb/prompts.py`, is frozen and unedited).
- **`rb/cli.py` — withhold condition-P text from the export.** Committed
  2026-11-14T23:09:52Z (git `198cd4a`). `export` now blanks `messages`/`text` for
  condition-P rows (which embed the project's promoter text), keeping their hashes and
  parsed numbers. This affects only the public export file; it does **not** affect which
  tokens are accepted or how responses are parsed.
- No other change was made to the acceptance filter, the discovery sources, or the
  response parser beyond items (a) and (b).

## (e) Third model added: Qwen3 (`qwen/qwen3.8-27b`) on Groq

- **Took effect:** 2026-11-14T23:32:06Z (runner restart banner in `data/run.log`).
- **Change:** a third model entry `groq-open-2` was added to `config.yaml`
  (`model: "qwen/qwen3.8-27b"`, Qwen3 from Alibaba, 27B; same Groq `base_url` and
  `GROQ_API_KEY` as `groq-open`; `rpm: 20`). It was chosen from a different maker than the
  OpenAI `gpt-oss-120b` already running, to add model breadth at no cost. xAI/Grok was
  skipped because its API requires paid credits.
- **Tokens collected without it:** **23** (tokens with `t0` before 23:32:06Z). Those 23
  tokens were asked only of `gemini-free` and `groq-open`; `groq-open-2` has responses only
  for tokens accepted from 23:32:06Z onward, so its n is smaller and is reported as such.
- **Validation and rate-limit watch:** `python -m rb models` confirmed it answered and
  parsed before the restart. In the 10 minutes after the restart the pre-existing Groq
  model (`groq-open`) recorded **0 rate-limit errors**, confirming the two do not share a
  limit that would degrade the existing model (Groq enforces per-model limits).
  `groq-open-2` itself hit its own per-model limit once (1 × HTTP 429 in ~29 calls,
  automatically retried; ~97% parse rate); this is handled and reported as part of qwen's
  unparsed/failed rate and does not affect the other models.
- **No outcome existed** at 23:32:06Z (earliest possible 6-hour outcome is
  2026-11-15T04:23:25Z), so this change could not have been outcome-influenced.

## Amendment anchor (on-chain)

The amended `config.yaml` and this `DEVIATIONS.md` are committed on-chain in an
**amendment** batch on Base Sepolia (chain 84532), giving the changes above a public
timestamp earlier than any outcome:

| Field | Value |
|---|---|
| Transaction | `0x2a8fa1d80b25db163a3fb7919b8f2551f7e2558ea0bbdf506d89de97532d3999` |
| Block time | 2026-11-14T23:46:48Z (before the earliest possible 6-hour outcome, 2026-11-15T04:23:25Z) |
| Merkle root | `284e38341eccfb665700b182b74c660ae3d48d20a2154bd9f0f935df142f8780` |
| Leaf — `config.yaml` | `440f518fcaac8b18b0f3044a4f2adb274ae4b9e39771e38faae1cffb06a5b865` |
| Leaf — `DEVIATIONS.md` | `facddd9cc1a0923fd9c202fa1da41f43a053a4477cdb2332308fc6ec662dead3` |
| Explorer | https://sepolia.basescan.org/tx/0x2a8fa1d80b25db163a3fb7919b8f2551f7e2558ea0bbdf506d89de97532d3999 |

The `DEVIATIONS.md` leaf is the SHA-256 of this file **as committed immediately before this
section was added** (git commit `fe4c557bf9514fc137b9e9e1dc252e854929514a`); the
`config.yaml` leaf is its current content. Both reproduce the transaction calldata
(`RESOLVEBENCH\x01` followed by the Merkle root). The original pre-registration remains
anchored in the prereg batch (tx `0xbf3a0edd…`); this amendment does not replace it — it
timestamps the documented changes.
