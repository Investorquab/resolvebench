"""RFC 6962 Merkle tree (the Certificate Transparency construction).

Leaves and interior nodes are domain-separated (0x00 / 0x01), so a leaf can never be
confused with a node. `root()` gives the value anchored on-chain; `path()` gives the
audit path for one record; `root_from_path()` lets anyone recompute the root from a
single record plus its path.
"""
import hashlib


def _h(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _leaf(d: bytes) -> bytes:
    return _h(b"\x00" + d)


def _node(left: bytes, right: bytes) -> bytes:
    return _h(b"\x01" + left + right)


def _split(n: int) -> int:
    k = 1
    while k * 2 < n:
        k *= 2
    return k


def root(leaves: list) -> bytes:
    n = len(leaves)
    if n == 0:
        return _h(b"")
    if n == 1:
        return _leaf(leaves[0])
    k = _split(n)
    return _node(root(leaves[:k]), root(leaves[k:]))


def path(m: int, leaves: list) -> list:
    n = len(leaves)
    if n <= 1:
        return []
    k = _split(n)
    if m < k:
        return path(m, leaves[:k]) + [root(leaves[k:])]
    return path(m - k, leaves[k:]) + [root(leaves[:k])]


def root_from_path(m: int, n: int, leaf: bytes, proof: list) -> bytes:
    if n <= 1:
        if proof:
            raise ValueError("proof too long")
        return _leaf(leaf)
    if not proof:
        raise ValueError("proof too short")
    k = _split(n)
    if m < k:
        return _node(root_from_path(m, k, leaf, proof[:-1]), proof[-1])
    return _node(proof[-1], root_from_path(m - k, n - k, leaf, proof[:-1]))
