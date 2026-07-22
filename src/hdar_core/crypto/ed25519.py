import os
import hashlib

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def generate_keypair() -> tuple[str, str]:
    if HAS_CRYPTO:
        priv = ed25519.Ed25519PrivateKey.generate()
        pub = priv.public_key()
        priv_bytes = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_bytes = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return priv_bytes.hex(), pub_bytes.hex()
    else:
        seed = os.urandom(32)
        pub = hashlib.sha256(b"PUB:" + seed).digest()
        return seed.hex(), pub.hex()


def sign_manifest(priv_hex: str, manifest_hash: str) -> str:
    if HAS_CRYPTO:
        priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(priv_hex))
        return priv.sign(bytes.fromhex(manifest_hash)).hex()
    return hashlib.sha256(bytes.fromhex(priv_hex) + bytes.fromhex(manifest_hash)).hexdigest()


def verify_manifest_sig(pub_hex: str, manifest_hash: str, sig_hex: str) -> bool:
    if HAS_CRYPTO:
        try:
            pub = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
            pub.verify(bytes.fromhex(sig_hex), bytes.fromhex(manifest_hash))
            return True
        except Exception:
            return False
    expected = hashlib.sha256(b"hash-only-fallback" + bytes.fromhex(manifest_hash)).hexdigest()
    return expected == sig_hex
