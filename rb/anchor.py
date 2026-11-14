"""Anchors a 32-byte Merkle root on Base as calldata of a zero-value transaction to
yourself. The block timestamp of that transaction is the public proof that every
response under the root existed before its outcome did.

No contract to deploy. Cost is the fee for a plain transfer with about 45 bytes of data.
The private key is read from an environment variable and never leaves this process.
"""
import logging
import os

log = logging.getLogger("rb")
TAG = b"RESOLVEBENCH\x01"  # 13-byte prefix so anchors are easy to find in calldata


def calldata(root_hex: str) -> str:
    return "0x" + TAG.hex() + root_hex


class NullAnchor:
    """Used when no key is configured: roots are still computed and stored locally."""
    enabled = False
    chain_id = 0

    def send(self, root_hex):
        return None


class BaseAnchor:
    enabled = True

    def __init__(self, cfg, http):
        from eth_account import Account
        self.http = http
        self.rpc = cfg.get("rpc", "https://mainnet.base.org")
        self.chain_id = int(cfg.get("chain_id", 8453))
        self.acct = Account.from_key(os.environ[cfg.get("key_env", "ANCHOR_PRIVATE_KEY")])
        self.address = self.acct.address

    def _rpc(self, method, params):
        status, data = self.http.post_json(self.rpc, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=30)
        if status != 200 or "error" in data:
            raise RuntimeError(f"{method}: {str(data.get('error') or data)[:200]}")
        return data["result"]

    def build(self, root_hex, nonce, gas_price, tip, gas):
        return {"type": 2, "chainId": self.chain_id, "nonce": nonce, "to": self.address, "value": 0,
                "data": calldata(root_hex), "gas": gas,
                "maxFeePerGas": 2 * gas_price + tip, "maxPriorityFeePerGas": tip}

    def sign(self, tx):
        signed = self.acct.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
        return "0x" + bytes(raw).hex()

    def send(self, root_hex):
        nonce = int(self._rpc("eth_getTransactionCount", [self.address, "pending"]), 16)
        gas_price = int(self._rpc("eth_gasPrice", []), 16)
        try:
            tip = int(self._rpc("eth_maxPriorityFeePerGas", []), 16)
        except Exception:
            tip = 1_000_000
        try:
            gas = int(int(self._rpc("eth_estimateGas", [{"from": self.address, "to": self.address,
                                                          "data": calldata(root_hex)}]), 16) * 1.3)
        except Exception:
            gas = 40_000
        return self._rpc("eth_sendRawTransaction", [self.sign(self.build(root_hex, nonce, gas_price, tip, gas))])

    def balance_eth(self):
        return int(self._rpc("eth_getBalance", [self.address, "latest"]), 16) / 1e18

    def lookup(self, tx_hash):
        return lookup_tx(self.http, self.rpc, tx_hash)


def lookup_tx(http, rpc, tx_hash):
    """Returns (calldata, block_timestamp) for an anchored transaction. Needs no key."""
    def call(method, params):
        status, data = http.post_json(rpc, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=30)
        if status != 200 or "error" in data:
            raise RuntimeError(f"{method}: {str(data.get('error') or data)[:200]}")
        return data["result"]
    tx = call("eth_getTransactionByHash", [tx_hash])
    if not tx or not tx.get("blockNumber"):
        return (tx or {}).get("input"), None
    blk = call("eth_getBlockByNumber", [tx["blockNumber"], False])
    return tx.get("input"), int(blk["timestamp"], 16)


def make_anchor(cfg, http):
    a = cfg.get("anchor") or {}
    if not a.get("enabled", True) or not os.environ.get(a.get("key_env", "ANCHOR_PRIVATE_KEY")):
        return NullAnchor()
    return BaseAnchor(a, http)
