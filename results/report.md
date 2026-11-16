# ResolveBench results

**Tokens accepted:** 64 | by source: {'dexscreener_boosts': 7, 'dexscreener_profiles': 53, 'geckoterminal_new_pools': 4}
**Screening:** {'accepted:accepted': 64, 'rejected:low_liquidity': 4755, 'rejected:no_priced_pair': 329, 'rejected:too_old': 16}

## Outcomes (base rates)

| Horizon | n | collapse | halve | strict rug | no pairs left |
|---|---|---|---|---|---|
| 1h | 64 | 0.234 | 0.391 | 0.172 | 0.000 |
| 6h | 64 | 0.312 | 0.547 | 0.250 | 0.000 |
| 24h | 64 | 0.484 | 0.750 | 0.400 | 0.016 |

## groq-open

| Condition | asked | valid | mean P(collapse 6h) | risk-on rate |
|---|---|---|---|---|
| A | 64 | 60 | 0.714 | 0.000 |
| B | 64 | 53 | 0.729 | 0.000 |
| C | 64 | 51 | 0.610 | 0.000 |
| P | 27 | 24 | 0.722 | 0.000 |
| D | 60 | 48 | 0.719 | 0.000 |
| D0 | 60 | 49 | 0.736 | 0.000 |

Accuracy of the neutral condition (A):

| Forecast | n | base rate | mean p | Brier | base-rate Brier | skill | AUC | ECE |
|---|---|---|---|---|---|---|---|---|
| p_collapse_6h | 60 | 0.317 | 0.714 | 0.377 | 0.216 | -0.742 | 0.521 | 0.397 |
| p_halve_6h | 60 | 0.550 | 0.548 | 0.251 | 0.247 | -0.013 | 0.548 | 0.035 |
| p_collapse_24h | 60 | 0.500 | 0.851 | 0.371 | 0.250 | -0.483 | 0.561 | 0.351 |

Paired change against A, mean [95% CI], * = interval excludes zero:

| Condition | change in P(collapse 6h) | change in risk-on rate | change in Brier (positive = worse) |
|---|---|---|---|
| B | +0.0113 [-0.0169, +0.0392] (n=52) | +0 [+0, +0] (n=52) | +0.0222 [-0.0127, +0.0568] (n=52) |
| C | -0.105 [-0.142, -0.0694]* (n=49) | +0 [+0, +0] (n=49) | -0.0726 [-0.119, -0.0287]* (n=49) |
| P | +0.00958 [-0.0358, +0.0533] (n=24) | +0 [+0, +0] (n=24) | +0.028 [-0.0256, +0.0833] (n=24) |
| D | +0.00708 [+0.000208, +0.0137]* (n=48) | +0 [+0, +0] (n=48) | +0.00401 [-0.0041, +0.0119] (n=48) |
| D0 | +0.0245 [+0.0188, +0.03]* (n=49) | +0 [+0, +0] (n=49) | +0.023 [+0.0139, +0.0323]* (n=49) |

| Flips after follow-up | n | under pressure (D) | plain re-check (D0) | excess |
|---|---|---|---|---|
| after_risk_off | 48 | 0.000 | 0.000 | +0 [+0, +0] (n=45) |
| after_risk_on | 0 | n/a | n/a | n/a |

Regret (share told buy/hold among tokens that collapsed within 6h): A: 0.000 (n=19), B: 0.000 (n=16), C: 0.000 (n=15), D: 0.000 (n=14)

## gemini-free

| Condition | asked | valid | mean P(collapse 6h) | risk-on rate |
|---|---|---|---|---|
| A | 64 | 64 | 0.739 | 0.016 |
| B | 64 | 64 | 0.798 | 0.000 |
| C | 64 | 64 | 0.694 | 0.031 |
| P | 27 | 27 | 0.700 | 0.000 |
| D | 64 | 64 | 0.725 | 0.000 |
| D0 | 64 | 64 | 0.742 | 0.000 |

Accuracy of the neutral condition (A):

| Forecast | n | base rate | mean p | Brier | base-rate Brier | skill | AUC | ECE |
|---|---|---|---|---|---|---|---|---|
| p_collapse_6h | 64 | 0.312 | 0.739 | 0.392 | 0.215 | -0.827 | 0.581 | 0.427 |
| p_halve_6h | 64 | 0.547 | 0.828 | 0.306 | 0.248 | -0.236 | 0.722 | 0.281 |
| p_collapse_24h | 64 | 0.484 | 0.896 | 0.414 | 0.250 | -0.659 | 0.559 | 0.412 |

Paired change against A, mean [95% CI], * = interval excludes zero:

| Condition | change in P(collapse 6h) | change in risk-on rate | change in Brier (positive = worse) |
|---|---|---|---|
| B | +0.0589 [+0.0391, +0.0792]* (n=64) | -0.0156 [-0.0469, +0] (n=64) | +0.0586 [+0.0303, +0.0869]* (n=64) |
| C | -0.0453 [-0.0672, -0.0242]* (n=64) | +0.0156 [-0.0312, +0.0625] (n=64) | -0.0263 [-0.0531, -0.00195]* (n=64) |
| P | -0.0167 [-0.0463, +0.0148] (n=27) | +0 [+0, +0] (n=27) | -0.00491 [-0.0449, +0.0378] (n=27) |
| D | -0.0141 [-0.0195, -0.00859]* (n=64) | -0.0156 [-0.0469, +0] (n=64) | -0.0118 [-0.019, -0.00473]* (n=64) |
| D0 | +0.0025 [-0.00109, +0.00688] (n=64) | -0.0156 [-0.0469, +0] (n=64) | +0.00292 [-0.00194, +0.0092] (n=64) |

| Flips after follow-up | n | under pressure (D) | plain re-check (D0) | excess |
|---|---|---|---|---|
| after_risk_off | 63 | 0.000 | 0.000 | +0 [+0, +0] (n=63) |
| after_risk_on | 1 | 1.000 | 1.000 | +0 [+0, +0] (n=1) |

Regret (share told buy/hold among tokens that collapsed within 6h): A: 0.000 (n=20), B: 0.000 (n=20), C: 0.000 (n=20), D: 0.000 (n=20)

## groq-open-2

| Condition | asked | valid | mean P(collapse 6h) | risk-on rate |
|---|---|---|---|---|
| A | 45 | 45 | 0.620 | 0.000 |
| B | 45 | 45 | 0.673 | 0.000 |
| C | 45 | 45 | 0.541 | 0.000 |
| P | 21 | 20 | 0.675 | 0.000 |
| D | 45 | 45 | 0.620 | 0.000 |
| D0 | 45 | 45 | 0.632 | 0.000 |

Accuracy of the neutral condition (A):

| Forecast | n | base rate | mean p | Brier | base-rate Brier | skill | AUC | ECE |
|---|---|---|---|---|---|---|---|---|
| p_collapse_6h | 45 | 0.400 | 0.620 | 0.347 | 0.240 | -0.447 | 0.469 | 0.338 |
| p_halve_6h | 45 | 0.600 | 0.733 | 0.243 | 0.240 | -0.011 | 0.646 | 0.182 |
| p_collapse_24h | 45 | 0.600 | 0.811 | 0.328 | 0.240 | -0.367 | 0.426 | 0.296 |

Paired change against A, mean [95% CI], * = interval excludes zero:

| Condition | change in P(collapse 6h) | change in risk-on rate | change in Brier (positive = worse) |
|---|---|---|---|
| B | +0.0533 [-0.0256, +0.131] (n=45) | +0 [+0, +0] (n=45) | +0.00222 [-0.0836, +0.0867] (n=45) |
| C | -0.0789 [-0.153, -0.00111]* (n=45) | +0 [+0, +0] (n=45) | -0.0306 [-0.12, +0.06] (n=45) |
| P | +0.16 [+0.03, +0.285]* (n=20) | +0 [+0, +0] (n=20) | +0.056 [-0.103, +0.214] (n=20) |
| D | +0 [+0, +0] (n=45) | +0 [+0, +0] (n=45) | +0 [+0, +0] (n=45) |
| D0 | +0.012 [-0.000222, +0.0233] (n=45) | +0 [+0, +0] (n=45) | +0.00914 [-0.00661, +0.0239] (n=45) |

| Flips after follow-up | n | under pressure (D) | plain re-check (D0) | excess |
|---|---|---|---|---|
| after_risk_off | 45 | 0.000 | 0.000 | +0 [+0, +0] (n=45) |
| after_risk_on | 0 | n/a | n/a | n/a |

Regret (share told buy/hold among tokens that collapsed within 6h): A: 0.000 (n=18), B: 0.000 (n=18), C: 0.000 (n=18), D: 0.000 (n=18)

**RugCheck score AUC for collapse at 6h (baseline):** 0.566
**Spend:** $0.00 over 932 calls (55 failed or unparsed)

## On-chain commitments

| Batch | kind | records | Merkle root | transaction |
|---|---|---|---|---|
| 1 | prereg | 3 | `6400825d51a352852fa082c74d5decbc9a79952980878075ec6bd0e88ae053fb` | https://sepolia.basescan.org/tx/0xbf3a0eddff127bbb3bd5020fe271477c96574bfc6f8652890a5c9dfbefedb6dc |
| 2 | responses | 140 | `c1e02d440723071589d4e5b8bd578225223c714b0577f8d48dc014a5a64efbd9` | https://sepolia.basescan.org/tx/0x07c152c8c89d72c67aff70b1b8c8614c965caa9ee9556d87a6306c03184b6d1a |
| 3 | responses | 10 | `787037bba54f976a0f66f055fe438d7667909131216c515346c9c493541ea80e` | https://sepolia.basescan.org/tx/0xdf115352b4f49f9e5bf75babfa2efdbe4560c1ddd9f7f513b239954613e091df |
| 4 | responses | 98 | `85dc57cb2aecba01132fbf87359b4db8ef945b7caf14b7f27b91f5cd4c5d9c37` | https://sepolia.basescan.org/tx/0x7fb5788f3a305e6d53c991aadb561e16ebead4366d18d1c62311d3333e853576 |
| 5 | responses | 40 | `f7fcbdb0fb03d8a74cc449c092f175f4809b00d091641557fc26d62ec009301b` | https://sepolia.basescan.org/tx/0x173f0eef549d3eaaf47da0f9d1f81734e16e5f64dfd6e36d8bed55a16a3dbe45 |
| 7 | amendment | 2 | `284e38341eccfb665700b182b74c660ae3d48d20a2154bd9f0f935df142f8780` | https://sepolia.basescan.org/tx/0x2a8fa1d80b25db163a3fb7919b8f2551f7e2558ea0bbdf506d89de97532d3999 |
| 8 | responses | 69 | `496dab75f3980abd67339ec8d767dbc6ff059148f1f8d678a18c3297246d9f4c` | https://sepolia.basescan.org/tx/0xba9dc75d527502fead4b7be390f7cb9453ba321736f26accfef9d1260aaaed6d |
| 9 | responses | 84 | `91e8514aad22578a065714148ddfdbbd53f54975a409abc30ca17710e0cef55f` | https://sepolia.basescan.org/tx/0x99a83ba008fcde73609f8d95b891b5a8f4dcab4f8fba0cdb2bfc05bffab185f2 |
| 10 | responses | 48 | `b03135bd928d0ceeb7c5c207762243368776b70909a260ea8b179ca47bfe7783` | https://sepolia.basescan.org/tx/0xb267a2dda2c7621fb50f40b9df8fdd9b352908cacf8bf8b0fadf10a4c92aaf52 |
| 11 | responses | 99 | `e9de51d63bf9d92486f19bf816e8fafdbf4a04c2cf949d4e8e4cc45c83e8e2ba` | https://sepolia.basescan.org/tx/0x9a252d629ab0ddab0e0459a2557f7cf63abfa51a83ba5740816d82f0c420d025 |
| 12 | responses | 61 | `dc552fe9638f507cd504a710c9c173310b56b6a2d9eb504886ffea0220fbff33` | https://sepolia.basescan.org/tx/0x6008a5ea3234c8c0fdbfcaa98e8fc0fe02ba2ceb52e545be71c46d7579e7b711 |
| 13 | responses | 25 | `12a8e6751bda35a0004189aa77d15533f3f512428bc2451bab6f15770395ce70` | https://sepolia.basescan.org/tx/0x626e289e122b64ebd8462adab815509224a985ac901c18ba6a1f7fdf4ac23e16 |
| 14 | responses | 43 | `26f1b9c59f4b8a0916385a05f8a1cf1e848614e80a8532ab297f6ac653aef97d` | https://sepolia.basescan.org/tx/0xb4c66b5aff447c32ffd741da45bee823b4fd112c821308dbe11b4dd3a15c1d95 |
| 15 | responses | 15 | `90610c65d8e1604091183461e1e62490eeca7700b95d3525aa2501dadaaa0ec1` | https://sepolia.basescan.org/tx/0x31de96adde0bc56d3c5ec6748cfcd1447822a52cfc9a42a613bc263061b96b22 |
| 16 | responses | 25 | `e55105d63eb36f41535624bd1bd8ed254945486e945ed165d4fc66ce958251da` | https://sepolia.basescan.org/tx/0x0d879f11e7f4b305fc6e0d003195b1b4d5d4f2582a5f5c8874e9fd3248b0faa5 |
| 17 | responses | 39 | `2a1b81724ba14e587450c3eb597b31981c13a7b276a5527f3fb6966b511fc106` | https://sepolia.basescan.org/tx/0x4631c787766cee24f730143e8d1e12404e72766481cb43bbb13bc38ee820da88 |
| 18 | responses | 49 | `6a4fa430c7e10a0bd6ab810f201e7d178314a472d82efef9c6d0a7f57bcd9f26` | https://sepolia.basescan.org/tx/0xda3b4c481e6ea18bf7155298990a6fc1b57065b31fb4566e14ac6afab7b72e60 |
| 19 | responses | 33 | `c122f40ecc3d887ed611a4436a67a22a3b573fa649d6f88f2b68fec03fe4f403` | https://sepolia.basescan.org/tx/0x3a5eb100bde36fb9c90c32098114bb92b8579f3e964e61922014614395ce5a89 |
