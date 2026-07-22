import hashlib
import hmac
from hdar_core.crypto.hashing import secure_compare_hashes


class SparseMerkleTree:
    """
    Production-grade 256-depth Sparse Merkle Tree (SMT) for workspace security.
    Represents a sparse key-value map over 2^256 address space.
    Supports cryptographic proofs of membership and proofs of non-membership.
    """
    def __init__(self):
        self.depth = 256
        self.empty_hashes = self._precompute_empty_hashes()
        self.db = {}
        self.values = {}
        self.root_hash = self.empty_hashes[self.depth]

    def _precompute_empty_hashes(self) -> list[str]:
        hashes = [hashlib.sha256(b"\x00" * 32).hexdigest()]
        for i in range(1, 257):
            prev = hashes[i - 1]
            parent = hashlib.sha256((prev + prev).encode('utf-8')).hexdigest()
            hashes.append(parent)
        return hashes

    def get_path_bits(self, key_hex: str) -> list[int]:
        val = int(key_hex, 16)
        bits = []
        for i in range(256):
            bits.append((val >> (255 - i)) & 1)
        return bits

    def insert(self, key_path: str, value_content: str):
        key_hex = hashlib.sha256(key_path.encode('utf-8')).hexdigest()
        value_hex = hashlib.sha256(value_content.encode('utf-8')).hexdigest()
        self.values[key_hex] = value_hex

        bits = self.get_path_bits(key_hex)
        
        current = self.root_hash
        path = []
        
        for depth_idx in range(self.depth):
            bit = bits[depth_idx]
            children = self.db.get(current)
            if children:
                left, right = children
            else:
                left = self.empty_hashes[self.depth - depth_idx - 1]
                right = self.empty_hashes[self.depth - depth_idx - 1]
            
            path.append((current, left, right))
            current = right if bit == 1 else left

        current = value_hex

        for depth_idx in reversed(range(self.depth)):
            bit = bits[depth_idx]
            _, left, right = path[depth_idx]
            
            if bit == 1:
                right = current
            else:
                left = current
                
            current = hashlib.sha256((left + right).encode('utf-8')).hexdigest()
            self.db[current] = (left, right)

        self.root_hash = current

    def get_proof(self, key_path: str) -> list[dict]:
        key_hex = hashlib.sha256(key_path.encode('utf-8')).hexdigest()
        bits = self.get_path_bits(key_hex)
        
        proof = []
        current = self.root_hash
        
        for depth_idx in range(self.depth):
            bit = bits[depth_idx]
            children = self.db.get(current)
            if children:
                left, right = children
            else:
                left = self.empty_hashes[self.depth - depth_idx - 1]
                right = self.empty_hashes[self.depth - depth_idx - 1]

            if bit == 1:
                proof.append({"position": "left", "hash": left})
                current = right
            else:
                proof.append({"position": "right", "hash": right})
                current = left
                
        return proof


def verify_smt_proof(key_path: str, value_content: str | None, proof: list[dict], root_hash: str) -> bool:
    key_hex = hashlib.sha256(key_path.encode('utf-8')).hexdigest()
    
    if value_content is not None:
        current = hashlib.sha256(value_content.encode('utf-8')).hexdigest()
    else:
        current = hashlib.sha256(b"\x00" * 32).hexdigest()

    val = int(key_hex, 16)
    bits = [(val >> (255 - i)) & 1 for i in range(256)]

    for depth_idx in reversed(range(256)):
        bit = bits[depth_idx]
        sibling = proof[depth_idx]["hash"]
        
        if bit == 1:
            current = hashlib.sha256((sibling + current).encode('utf-8')).hexdigest()
        else:
            current = hashlib.sha256((current + sibling).encode('utf-8')).hexdigest()
            
    return secure_compare_hashes(current, root_hash)
