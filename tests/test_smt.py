import pytest
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from hdar_core.crypto.merkle import SparseMerkleTree, verify_smt_proof
from hdar_core.attestation.host import HostAttestationEngine


def test_merkle_tree_determinism():
    tree1 = SparseMerkleTree()
    tree2 = SparseMerkleTree()
    
    tree1.insert("a.txt", "hash_a")
    tree2.insert("a.txt", "hash_a")
    
    assert tree1.root_hash == tree2.root_hash
    assert len(tree1.root_hash) == 64


def test_merkle_membership_proof():
    tree = SparseMerkleTree()
    tree.insert("a.txt", "hash_a")
    tree.insert("b.txt", "hash_b")
    
    # Generate proof for a.txt
    proof = tree.get_proof("a.txt")
    assert proof is not None
    assert len(proof) == 256
    
    # Verify proof of membership
    is_valid = verify_smt_proof("a.txt", "hash_a", proof, tree.root_hash)
    assert is_valid is True
    
    # Verify proof of non-membership
    proof_non = tree.get_proof("c.txt")
    is_non_valid = verify_smt_proof("c.txt", None, proof_non, tree.root_hash)
    assert is_non_valid is True


def test_host_attestation():
    engine = HostAttestationEngine(host_label="test-runner")
    payload = engine.collect_attestation_payload()
    
    assert payload["host_label"] == "test-runner"
    assert "os_platform" in payload
    assert "cpu_architecture" in payload
    
    # Test signing
    priv_key_hex = "00" * 32
    attest_report = engine.sign_attestation(payload, priv_key_hex)
    assert "signature" in attest_report
    assert len(attest_report["payload_hash"]) == 64
