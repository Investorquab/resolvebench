# Anchoring transactions (Base Sepolia, chain id 84532)

Every 30 minutes the new response leaves form an RFC 6962 Merkle tree whose root is
written to Base Sepolia as transaction calldata. The pre-registration (batch 1) and an
on-chain amendment (batch 7) are anchored the same way. Each roots commitment precedes
the outcomes it covers. Verify any response with `python -m rb verify <response_id>`.

| Batch | Kind | Records | UTC time | Merkle root | Transaction |
|---|---|---|---|---|---|
| 1 | prereg | 3 | 2026-11-14 22:23:24 | `6400825d51a35285...` | [`0xbf3a0eddff12...`](https://sepolia.basescan.org/tx/0xbf3a0eddff127bbb3bd5020fe271477c96574bfc6f8652890a5c9dfbefedb6dc) |
| 2 | responses | 140 | 2026-11-14 22:53:26 | `c1e02d4407230715...` | [`0x07c152c8c89d...`](https://sepolia.basescan.org/tx/0x07c152c8c89d72c67aff70b1b8c8614c965caa9ee9556d87a6306c03184b6d1a) |
| 3 | responses | 10 | 2026-11-14 23:17:03 | `787037bba54f976a...` | [`0xdf115352b4f4...`](https://sepolia.basescan.org/tx/0xdf115352b4f49f9e5bf75babfa2efdbe4560c1ddd9f7f513b239954613e091df) |
| 4 | responses | 98 | 2026-11-14 23:32:04 | `85dc57cb2aecba01...` | [`0x7fb5788f3a30...`](https://sepolia.basescan.org/tx/0x7fb5788f3a305e6d53c991aadb561e16ebead4366d18d1c62311d3333e853576) |
| 5 | responses | 40 | 2026-11-14 23:44:44 | `f7fcbdb0fb03d8a7...` | [`0x173f0eef549d...`](https://sepolia.basescan.org/tx/0x173f0eef549d3eaaf47da0f9d1f81734e16e5f64dfd6e36d8bed55a16a3dbe45) |
| 7 | amendment | 2 | 2026-11-14 23:46:47 | `284e38341eccfb66...` | [`0x2a8fa1d80b25...`](https://sepolia.basescan.org/tx/0x2a8fa1d80b25db163a3fb7919b8f2551f7e2558ea0bbdf506d89de97532d3999) |
| 8 | responses | 69 | 2026-11-15 00:15:06 | `496dab75f3980abd...` | [`0xba9dc75d5275...`](https://sepolia.basescan.org/tx/0xba9dc75d527502fead4b7be390f7cb9453ba321736f26accfef9d1260aaaed6d) |
| 9 | responses | 84 | 2026-11-15 00:45:07 | `91e8514aad22578a...` | [`0x99a83ba008fc...`](https://sepolia.basescan.org/tx/0x99a83ba008fcde73609f8d95b891b5a8f4dcab4f8fba0cdb2bfc05bffab185f2) |
| 10 | responses | 48 | 2026-11-15 01:15:08 | `b03135bd928d0cee...` | [`0xb267a2dda2c7...`](https://sepolia.basescan.org/tx/0xb267a2dda2c7621fb50f40b9df8fdd9b352908cacf8bf8b0fadf10a4c92aaf52) |
| 11 | responses | 99 | 2026-11-15 01:45:10 | `e9de51d63bf9d924...` | [`0x9a252d629ab0...`](https://sepolia.basescan.org/tx/0x9a252d629ab0ddab0e0459a2557f7cf63abfa51a83ba5740816d82f0c420d025) |
| 12 | responses | 61 | 2026-11-15 02:15:11 | `dc552fe9638f507c...` | [`0x6008a5ea3234...`](https://sepolia.basescan.org/tx/0x6008a5ea3234c8c0fdbfcaa98e8fc0fe02ba2ceb52e545be71c46d7579e7b711) |
| 13 | responses | 25 | 2026-11-15 02:45:13 | `12a8e6751bda35a0...` | [`0x626e289e122b...`](https://sepolia.basescan.org/tx/0x626e289e122b64ebd8462adab815509224a985ac901c18ba6a1f7fdf4ac23e16) |
| 14 | responses | 43 | 2026-11-15 03:45:14 | `26f1b9c59f4b8a09...` | [`0xb4c66b5aff44...`](https://sepolia.basescan.org/tx/0xb4c66b5aff447c32ffd741da45bee823b4fd112c821308dbe11b4dd3a15c1d95) |
| 15 | responses | 15 | 2026-11-15 04:15:15 | `90610c65d8e16040...` | [`0x31de96adde0b...`](https://sepolia.basescan.org/tx/0x31de96adde0bc56d3c5ec6748cfcd1447822a52cfc9a42a613bc263061b96b22) |
| 16 | responses | 25 | 2026-11-15 04:45:16 | `e55105d63eb36f41...` | [`0x0d879f11e7f4...`](https://sepolia.basescan.org/tx/0x0d879f11e7f4b305fc6e0d003195b1b4d5d4f2582a5f5c8874e9fd3248b0faa5) |
| 17 | responses | 39 | 2026-11-15 05:15:16 | `2a1b81724ba14e58...` | [`0x4631c787766c...`](https://sepolia.basescan.org/tx/0x4631c787766cee24f730143e8d1e12404e72766481cb43bbb13bc38ee820da88) |
| 18 | responses | 49 | 2026-11-15 05:45:16 | `6a4fa430c7e10a0b...` | [`0xda3b4c481e6e...`](https://sepolia.basescan.org/tx/0xda3b4c481e6ea18bf7155298990a6fc1b57065b31fb4566e14ac6afab7b72e60) |
| 19 | responses | 33 | 2026-11-15 06:15:17 | `c122f40ecc3d887e...` | [`0x3a5eb100bde3...`](https://sepolia.basescan.org/tx/0x3a5eb100bde36fb9c90c32098114bb92b8579f3e964e61922014614395ce5a89) |

**18 transactions total.** Full roots and leaves are in `results/public/batches.jsonl`.
