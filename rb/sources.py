"""Market data: DexScreener (discovery, prices), RugCheck (holders, authorities),
GeckoTerminal (optional discovery). No API keys needed for any of them.

Also builds the frozen T0 snapshot and the plain-text "facts card" shown to models.
"""
import hashlib
import json
import logging
import random
import time

import httpx

log = logging.getLogger("rb")


def canon(obj) -> str:
    """Canonical JSON: the exact bytes that get hashed."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(s) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


class Http:
    def __init__(self, timeout=30):
        self.c = httpx.Client(timeout=timeout, follow_redirects=True, headers={
            "accept": "application/json", "user-agent": "resolvebench/0.1 (research sprint)"})

    def get_json(self, url, tries=4, ok_missing=False, **kw):
        last = None
        for i in range(tries):
            try:
                r = self.c.get(url, **kw)
                if r.status_code == 200:
                    return r.json()
                last = f"HTTP {r.status_code}"
                if r.status_code in (400, 404):
                    if ok_missing:
                        return None
                    break
            except Exception as e:  # network errors, bad JSON
                last = repr(e)
            time.sleep(min(20, 1.5 * 2 ** i) + random.random())
        raise RuntimeError(f"GET {url} failed: {last}")

    def post_json(self, url, body, headers=None, timeout=120):
        r = self.c.post(url, json=body, headers=headers or {}, timeout=timeout)
        try:
            data = r.json()
        except Exception:
            data = {"raw": r.text[:500]}
        return r.status_code, data


class DexScreener:
    BASE = "https://api.dexscreener.com"

    def __init__(self, http):
        self.http = http

    def _feed(self, path):
        out = []
        for it in self.http.get_json(self.BASE + path) or []:
            if it.get("chainId") == "solana" and it.get("tokenAddress"):
                out.append((it["tokenAddress"], (it.get("description") or "").strip()))
        return out

    def profiles(self):
        """Tokens that just published a DexScreener profile, i.e. are being promoted."""
        return self._feed("/token-profiles/latest/v1")

    def boosts(self):
        """Tokens that just paid for a DexScreener boost."""
        return self._feed("/token-boosts/latest/v1")

    def tokens(self, mints):
        """All pairs for up to 30 mints. Returns a flat list of pair objects."""
        data = self.http.get_json(f"{self.BASE}/tokens/v1/solana/{','.join(mints)}")
        if isinstance(data, dict):  # older response shape
            data = data.get("pairs") or []
        return data or []


class GeckoTerminal:
    BASE = "https://api.geckoterminal.com/api/v2"

    def __init__(self, http, pages=2):
        self.http, self.pages = http, pages

    def new_pools(self):
        out = []
        for p in range(1, self.pages + 1):
            data = self.http.get_json(f"{self.BASE}/networks/solana/new_pools?page={p}", tries=2)
            for it in (data or {}).get("data", []):
                tid = (((it.get("relationships") or {}).get("base_token") or {}).get("data") or {}).get("id", "")
                if tid.startswith("solana_"):
                    out.append((tid[len("solana_"):], ""))
        return out


class RugCheck:
    BASE = "https://api.rugcheck.xyz/v1"

    def __init__(self, http):
        self.http = http

    def report(self, mint):
        try:
            return self.http.get_json(f"{self.BASE}/tokens/{mint}/report", tries=2, ok_missing=True)
        except Exception as e:
            log.warning("rugcheck %s: %s", mint, e)
            return None


# ---------- pair aggregation ----------

def pairs_of(mint, pairs):
    return [p for p in pairs if ((p.get("baseToken") or {}).get("address") == mint)]


def aggregate(pairs):
    """Price from the deepest pool, liquidity summed over all pools of the token.

    Summing across pools means a pool migration (for example bonding curve to AMM)
    is not mistaken for a liquidity pull.
    """
    best, best_liq, total = None, -1.0, 0.0
    for p in pairs:
        liq = num((p.get("liquidity") or {}).get("usd")) or 0.0
        total += liq
        if num(p.get("priceUsd")) is not None and liq > best_liq:
            best, best_liq = p, liq
    if best is None:
        return None, None, 0.0
    return best, num(best.get("priceUsd")), total


# ---------- snapshot ----------

def build_snapshot(mint, pairs, now, flt):
    """Returns (ok, reason, snapshot). Applies the pre-registered inclusion filter."""
    best, price, liq = aggregate(pairs)
    if best is None or not price or price <= 0:
        return False, "no_priced_pair", None
    created = [num(p.get("pairCreatedAt")) for p in pairs if num(p.get("pairCreatedAt"))]
    age_min = (now - min(created) / 1000.0) / 60.0 if created else None
    tx = best.get("txns") or {}
    h1 = tx.get("h1") or {}
    n_h1 = (h1.get("buys") or 0) + (h1.get("sells") or 0)
    if liq < flt.get("min_liquidity_usd", 10000):
        return False, "low_liquidity", None
    if age_min is None:
        return False, "no_age", None
    if age_min < flt.get("min_age_minutes", 5):
        return False, "too_new", None
    if age_min > flt.get("max_age_hours", 24) * 60:
        return False, "too_old", None
    if n_h1 < flt.get("min_txns_h1", 20):
        return False, "inactive", None
    info = best.get("info") or {}
    socials = {(s.get("type") or "").lower() for s in info.get("socials") or []}
    vol, chg, m5 = best.get("volume") or {}, best.get("priceChange") or {}, tx.get("m5") or {}
    snap = {
        "mint": mint,
        "t0": int(now),
        "symbol": (best.get("baseToken") or {}).get("symbol"),
        "name": (best.get("baseToken") or {}).get("name"),
        "quote": (best.get("quoteToken") or {}).get("symbol"),
        "dex": best.get("dexId"),
        "pair": best.get("pairAddress"),
        "n_pairs": len(pairs),
        "age_minutes": round(age_min, 1),
        "price_usd": price,
        "liquidity_usd": round(liq, 2),
        "market_cap_usd": num(best.get("marketCap")) or num(best.get("fdv")),
        "volume_m5": num(vol.get("m5")), "volume_h1": num(vol.get("h1")), "volume_h6": num(vol.get("h6")),
        "buys_m5": m5.get("buys"), "sells_m5": m5.get("sells"),
        "buys_h1": h1.get("buys"), "sells_h1": h1.get("sells"),
        "chg_m5": num(chg.get("m5")), "chg_h1": num(chg.get("h1")), "chg_h6": num(chg.get("h6")),
        "has_website": bool(info.get("websites")),
        "has_twitter": bool(socials & {"twitter", "x"}),
        "has_telegram": "telegram" in socials,
        "boost_active": bool((best.get("boosts") or {}).get("active")),
    }
    return True, "accepted", snap


def enrich(snap, rc):
    """Adds holder and authority facts from RugCheck. RugCheck's own risk score is kept
    out of the card on purpose: it is a baseline to compare models against."""
    snap["rugcheck_ok"] = bool(rc)
    if not rc:
        return None
    known = set((rc.get("knownAccounts") or {}).keys())
    holders = [h for h in rc.get("topHolders") or []
               if h.get("address") not in known and h.get("owner") not in known]
    top10 = sum(num(h.get("pct")) or 0 for h in holders[:10])
    supply = num((rc.get("token") or {}).get("supply"))
    cb = num(rc.get("creatorBalance"))
    markets = rc.get("markets") or []
    lp_locked = None
    if markets:
        def size(m):
            lp = m.get("lp") or {}
            return (num(lp.get("quoteUSD")) or 0) + (num(lp.get("baseUSD")) or 0)
        lp_locked = num((max(markets, key=size).get("lp") or {}).get("lpLockedPct"))
    snap.update({
        "holders": rc.get("totalHolders"),
        "top10_pct": round(top10, 1) if holders else None,
        "creator_pct": round(100 * cb / supply, 2) if (cb is not None and supply) else None,
        "mint_authority_active": rc.get("mintAuthority") is not None,
        "freeze_authority_active": rc.get("freezeAuthority") is not None,
        "metadata_mutable": (rc.get("tokenMeta") or {}).get("mutable"),
        "lp_locked_pct": round(lp_locked, 1) if lp_locked is not None else None,
        "insider_wallets": rc.get("graphInsidersDetected"),
        "transfer_fee_pct": num((rc.get("transferFee") or {}).get("pct")),
        "launchpad": (rc.get("launchpad") or {}).get("name"),
    })
    return num(rc.get("score_normalised"))


def _money(v):
    if v is None:
        return "unknown"
    if v >= 1:
        return f"${v:,.0f}"
    return f"${v:.10f}".rstrip("0")


def _pct(v, signed=False):
    if v is None:
        return "unknown"
    return f"{v:+.1f}%" if signed else f"{v:.1f}%"


def _yn(v, yes="yes", no="no"):
    return "unknown" if v is None else (yes if v else no)


def _n(v):
    return "unknown" if v is None else f"{v:,}"


def render_card(s):
    """The exact text every model sees. Deterministic: same snapshot, same card."""
    age = s["age_minutes"]
    age_txt = f"{age:.0f} minutes" if age < 120 else f"{age / 60:.1f} hours"
    lines = [
        f"Token: {s.get('name')} ({s.get('symbol')}) on Solana",
        f"Main pool: {s.get('symbol')}/{s.get('quote')} on {s.get('dex')}, first traded {age_txt} ago",
        f"Price: {_money(s['price_usd'])} | Market cap: {_money(s.get('market_cap_usd'))} | Pool liquidity: {_money(s['liquidity_usd'])}",
        f"Volume: {_money(s.get('volume_m5'))} (5 min), {_money(s.get('volume_h1'))} (1 hour), {_money(s.get('volume_h6'))} (6 hours)",
        f"Trades: {_n(s.get('buys_h1'))} buys / {_n(s.get('sells_h1'))} sells (1 hour); {_n(s.get('buys_m5'))} buys / {_n(s.get('sells_m5'))} sells (5 min)",
        f"Price change: {_pct(s.get('chg_m5'), True)} (5 min), {_pct(s.get('chg_h1'), True)} (1 hour), {_pct(s.get('chg_h6'), True)} (6 hours)",
        f"Holders: {_n(s.get('holders'))} | Top 10 wallets hold {_pct(s.get('top10_pct'))} (liquidity pool excluded) | Creator holds {_pct(s.get('creator_pct'))}",
        f"Mint authority: {_yn(s.get('mint_authority_active'), 'ACTIVE', 'revoked')} | Freeze authority: {_yn(s.get('freeze_authority_active'), 'ACTIVE', 'revoked')} | Metadata mutable: {_yn(s.get('metadata_mutable'))}",
        f"LP tokens locked or burned: {_pct(s.get('lp_locked_pct'))} | Transfer tax: {_pct(s.get('transfer_fee_pct'))}",
        f"Wallets flagged as linked insiders: {_n(s.get('insider_wallets'))}",
        f"Launchpad: {s.get('launchpad') or 'unknown'} | Website: {_yn(s.get('has_website'))} | X account: {_yn(s.get('has_twitter'))} | Telegram: {_yn(s.get('has_telegram'))} | Paid promotion on DexScreener: {_yn(s.get('boost_active'))}",
    ]
    return "\n".join(lines)
