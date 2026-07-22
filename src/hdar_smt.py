import hashlib
import json
from pathlib import Path


class MerkleNode:
    def __init__(self, left, right, value: str, is_leaf: bool = False):
        self.left = left
        self.right = right
        self.value = value
        self.is_leaf = is_leaf


class SparseMerkleTree:
    """
    Binary Merkle Tree indexing engine for autonomous agent workspaces.
    Enables O(log N) membership proof verification of individual files.
    """
    def __init__(self, files_list: list[dict]):
        # Sort files to ensure deterministic Merkle root
        self.files = sorted(files_list, key=lambda x: x["rel_path"])
        self.leaves = [self._compute_leaf_hash(f) for f in self.files]
        self.root_node = self._build_tree()

    def _compute_leaf_hash(self, file_entry: dict) -> str:
        # leaf = SHA256(rel_path | sha256 | size | mode)
        material = f"{file_entry['rel_path']}|{file_entry['sha256']}|{file_entry['size']}|{file_entry['mode']}"
        return hashlib.sha256(material.encode('utf-8')).hexdigest()

    def _build_tree(self) -> MerkleNode | None:
        if not self.leaves:
            empty_hash = hashlib.sha256(b"").hexdigest()
            return MerkleNode(None, None, empty_hash, is_leaf=True)

        nodes = [MerkleNode(None, None, val, is_leaf=True) for val in self.leaves]
        
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                if i + 1 < len(nodes):
                    right = nodes[i + 1]
                else:
                    # Duplicate left node if odd number of elements at level
                    right = MerkleNode(None, None, left.value, is_leaf=left.is_leaf)
                
                # Parent = SHA256(Left.value + Right.value)
                parent_hash = hashlib.sha256((left.value + right.value).encode('utf-8')).hexdigest()
                parent_node = MerkleNode(left, right, parent_hash)
                next_level.append(parent_node)
            nodes = next_level
            
        return nodes[0]

    @property
    def root_hash(self) -> str:
        return self.root_node.value if self.root_node else hashlib.sha256(b"").hexdigest()

    def get_membership_proof(self, rel_path: str) -> list[dict] | None:
        """Generates audit proof paths for a specific file relative path."""
        target_idx = -1
        for i, f in enumerate(self.files):
            if f["rel_path"] == rel_path:
                target_idx = i
                break
        
        if target_idx == -1:
            return None

        proof = []
        nodes = [MerkleNode(None, None, val, is_leaf=True) for val in self.leaves]
        idx = target_idx

        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                if i + 1 < len(nodes):
                    right = nodes[i + 1]
                else:
                    right = MerkleNode(None, None, left.value, is_leaf=left.is_leaf)
                
                parent_hash = hashlib.sha256((left.value + right.value).encode('utf-8')).hexdigest()
                parent_node = MerkleNode(left, right, parent_hash)
                next_level.append(parent_node)

            # Record sibling info
            if idx % 2 == 0:
                # Sibling is to the right
                proof.append({"position": "right", "hash": nodes[idx + 1].value if idx + 1 < len(nodes) else nodes[idx].value})
            else:
                # Sibling is to the left
                proof.append({"position": "left", "hash": nodes[idx - 1].value})

            idx = idx // 2
            nodes = next_level

        return proof


def verify_membership_proof(leaf_hash: str, proof: list[dict], root_hash: str) -> bool:
    """Verifies membership proof of a leaf node against the Merkle root."""
    current = leaf_hash
    for step in proof:
        sibling = step["hash"]
        if step["position"] == "left":
            current = hashlib.sha256((sibling + current).encode('utf-8')).hexdigest()
        else:
            current = hashlib.sha256((current + sibling).encode('utf-8')).hexdigest()
            
    return hmac_compare(current, root_hash)


def hmac_compare(h1: str, h2: str) -> bool:
    import hmac
    return hmac.compare_digest(h1.lower().encode(), h2.lower().encode())
