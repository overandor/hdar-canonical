import pytest
from src.hdar_smt import SparseMerkleTree, verify_membership_proof
from src.hdar_secure_enclave import HostAttestationEngine


def test_merkle_tree_determinism():
    files = [
        {"rel_path": "a.txt", "sha256": "hash_a", "size": 10, "mode": 0o644},
        {"rel_path": "b.txt", "sha256": "hash_b", "size": 20, "mode": 0o644}
    ]
    tree1 = SparseMerkleTree(files)
    tree2 = SparseMerkleTree(files)
    
    assert tree1.root_hash == tree2.root_hash
    assert len(tree1.root_hash) == 64


def test_merkle_membership_proof():
    files = [
        {"rel_path": "a.txt", "sha256": "hash_a", "size": 10, "mode": 0o644},
        {"rel_path": "b.txt", "sha256": "hash_b", "size": 20, "mode": 0o644},
        {"rel_path": "c.txt", "sha256": "hash_c", "size": 30, "mode": 0o644}
    ]
    tree = SparseMerkleTree(files)
    
    # Generate proof for a.txt
    proof = tree.get_membership_proof("a.txt")
    assert proof is not None
    assert len(proof) == 2
    
    # Verify proof
    leaf_hash = tree._compute_leaf_hash(files[0])
    is_valid = verify_membership_proof(leaf_hash, proof, tree.root_hash)
    assert is_valid is True
    
    # Negative test
    is_valid_wrong = verify_membership_proof(leaf_hash, proof, "wrong_root_hash_999")
    assert is_valid_wrong is False


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
