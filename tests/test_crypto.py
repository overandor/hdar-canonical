"""Test Ed25519 signing and hash-only fallback."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hdar import (
    generate_keypair,
    sign_message,
    verify_signature,
    sha256_bytes,
    HAS_CRYPTO,
)


class TestKeypair:
    def test_generates_different_keys(self):
        priv1, pub1 = generate_keypair()
        priv2, pub2 = generate_keypair()
        assert priv1 != priv2
        assert pub1 != pub2

    def test_key_lengths(self):
        priv, pub = generate_keypair()
        if HAS_CRYPTO:
            assert len(priv) == 32
            assert len(pub) == 32
        else:
            assert len(priv) > 0
            assert len(pub) > 0


class TestSignVerify:
    def test_valid_signature(self):
        priv, pub = generate_keypair()
        msg = b"test message for signing"
        sig = sign_message(priv, msg)
        assert verify_signature(pub, msg, sig) is True

    def test_wrong_message_rejected(self):
        priv, pub = generate_keypair()
        sig = sign_message(priv, b"original message")
        assert verify_signature(pub, b"tampered message", sig) is False

    def test_wrong_key_rejected(self):
        priv1, pub1 = generate_keypair()
        priv2, pub2 = generate_keypair()
        sig = sign_message(priv1, b"message")
        assert verify_signature(pub2, b"message", sig) is False

    def test_empty_message(self):
        priv, pub = generate_keypair()
        sig = sign_message(priv, b"")
        assert verify_signature(pub, b"", sig) is True

    def test_large_message(self):
        priv, pub = generate_keypair()
        msg = b"x" * 100_000
        sig = sign_message(priv, msg)
        assert verify_signature(pub, msg, sig) is True


class TestHashPrimitives:
    def test_sha256_bytes_known_vector(self):
        assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_sha256_bytes_hello(self):
        assert sha256_bytes(b"hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_canonical_json_deterministic(self):
        from hdar import canonical_json
        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        assert canonical_json(d1) == canonical_json(d2)
