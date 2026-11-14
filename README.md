# ResolveBench

An evaluation of chatbot decision advice where the answer key does not exist yet when
the model answers. Models are asked whether to buy or hold newly launched Solana
tokens under neutral, hype, sunk-cost and pushback conditions. Every response is
hashed and anchored on Base Sepolia, then graded against what the token actually did 6 and 24
hours later.

Study design and hypotheses: [PREREG.md](PREREG.md). Exact prompts: [rb/prompts.py](rb/prompts.py).

## Run it (about 30 minutes to first data)

```bash
unzip resolvebench.zip && cd resolvebench
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m tests.test_offline          # no network needed; must end with ALL OFFLINE TESTS PASSED
```

**1. Check the data feeds (no keys needed).**

```bash
python -m rb probe --minutes 5
```

Look at three things in the output: every feed answers, "roughly N candidates per
hour" is at least 30, and some tokens pass the filter. If few pass, lower
`filters.min_liquidity_usd` in `config.yaml` and probe again.

**2. Add keys.**

```bash
cp .env.example .env && chmod 600 .env && nano .env
```

Fill in only the keys you have: a model whose key is blank is skipped, so the same
config works for anyone. Keys stay in `.env` on this machine; it is gitignored. Use a
new, empty wallet for `ANCHOR_PRIVATE_KEY` and fund it from a Base Sepolia faucet.

**3. Pick models.**

```bash
python -m rb catalog grok       # list the ids each provider offers; also try gemini, haiku, or no word at all
python -m rb models             # one real question per model, with cost per token
```

Put the ids in `config.yaml` where it says `<id from ...>` and re-run `models` until
every model you have a key for says OK. Free keys have an `rpm` setting; set it to
your tier's limit.

**4. Freeze the config, then start.** `config.yaml`, `PREREG.md` and `rb/prompts.py`
are hashed and anchored the moment `run` starts. Do not edit them afterwards; if you
must, write down what and why (it goes in the report as a deviation).

```bash
tmux new -s rb '. .venv/bin/activate && python -m rb run'     # Ctrl-b d to detach
python -m rb status                                           # from another shell, any time
```

For a process that survives reboots, use `deploy/resolvebench.service` instead.

**5. Results.**

```bash
python -m rb report            # labels outcomes, writes results/report.md and results.json
python -m rb verify 42         # proves response 42 was on-chain before its outcome
python -m rb export            # public data files for the repo
```

`report` works while collection is live. The 1-hour numbers show up first; they are
descriptive only. The pre-registered primary outcome is at 6 hours.

## What runs when

| Every | What |
|---|---|
| 3 min | look for new tokens, freeze a snapshot, ask every model (A, B, C, P, then D and D0) |
| 10 min | record price and liquidity for every token younger than 25.5 hours |
| 30 min | Merkle root of all new responses, anchored on Base Sepolia |

Collection stops at `run.collect_until`, at `run.max_tokens_total`, or when spend
reaches `run.budget_usd`. Tracking and anchoring keep going. The process can be
killed and restarted at any point: nothing is asked twice.

## Files

| File | Role |
|---|---|
| `rb/sources.py` | DexScreener, RugCheck, GeckoTerminal clients; snapshot and facts card |
| `rb/prompts.py` | condition wording and response parser |
| `rb/models.py` | client for any OpenAI-compatible API |
| `rb/run.py` | the runner |
| `rb/merkle.py`, `rb/anchor.py` | RFC 6962 tree and the Base transaction |
| `rb/resolve.py`, `rb/report.py` | outcome labels and the pre-registered analysis |
| `tests/test_offline.py` | end-to-end test with a fake market, fake models and a simulated clock |

## Known limits

- The three data APIs could not be called from the machine this was written on. Their
  response shapes were read from live responses and the parsers are tested against
  matching fakes, but `probe` on your VPS is the first real contact.
- Anchoring proves responses were not changed after the fact. It does not prove which
  model produced them.
- DexScreener's profile and boost feeds over-represent promoted tokens. Results are
  reported by source.
