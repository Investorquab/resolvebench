"""Turns price observations into outcome labels, exactly as pre-registered.

For each horizon the label uses the first observation at or after T0 + horizon
(accepted up to 30 minutes late). Ratios are against the T0 snapshot.

  collapse = price <= 10% of T0  OR  liquidity <= 20% of T0  OR  token has no pairs
  halve    = price <= 50% of T0  OR  token has no pairs
  strict   = price <= 10% AND liquidity <= 20% (or no pairs), and still true at the
             next observation 30 to 90 minutes later
"""
HORIZONS = {"1h": 3600, "6h": 21600, "24h": 86400}
LATE_OK = 1800


def _ratios(o, tok):
    if not o["found"] or o["price"] is None:
        return None, None, 1
    pr = o["price"] / tok["price0"] if tok["price0"] else None
    lr = (o["liq"] or 0.0) / tok["liq0"] if tok["liq0"] else None
    return pr, lr, 0


def _strict(o, tok):
    pr, lr, gone = _ratios(o, tok)
    return bool(gone or (pr is not None and lr is not None and pr <= 0.10 and lr <= 0.20))


def resolve(db, now):
    """Idempotent. Returns {horizon: (resolved, pending, missing)}."""
    stats = {h: [0, 0, 0] for h in HORIZONS}
    for tok in db.q("SELECT mint, t0, price0, liq0 FROM tokens"):
        obs = db.q("SELECT * FROM obs WHERE mint=? ORDER BY ts", (tok["mint"],))
        for h, sec in HORIZONS.items():
            target = tok["t0"] + sec
            hit = [o for o in obs if target <= o["ts"] <= target + LATE_OK]
            if not hit:
                stats[h][1 if now < target + LATE_OK else 2] += 1
                continue
            o = hit[0]
            pr, lr, gone = _ratios(o, tok)
            collapse = int(bool(gone or (pr is not None and pr <= 0.10) or (lr is not None and lr <= 0.20)))
            halve = int(bool(gone or (pr is not None and pr <= 0.50)))
            later = [x for x in obs if o["ts"] + 1800 <= x["ts"] <= o["ts"] + 5400]
            strict = int(_strict(o, tok) and _strict(later[0], tok)) if later else None
            db.x("INSERT OR REPLACE INTO outcomes VALUES(?,?,?,?,?,?,?,?,?)",
                 (tok["mint"], h, o["ts"], pr, lr, gone, collapse, halve, strict))
            stats[h][0] += 1
    return {h: tuple(v) for h, v in stats.items()}
