import sys
import os
import platform
import json
import hashlib
import time

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class HostAttestationEngine:
    """
    Collects secure host and execution platform attestations (OS, CPU, Hostname),
    establishing hardware-aligned identity for host executors.
    """
    def __init__(self, host_label: str = "docker-sandbox"):
        self.host_label = host_label

    def collect_attestation_payload(self) -> dict:
        return {
            "attestation_version": "1.1.0",
            "host_label": self.host_label,
            "os_platform": sys.platform,
            "os_release": platform.release(),
            "cpu_architecture": platform.machine(),
            "python_version": sys.version.split()[0],
            "timestamp": time.time(),
            "entropy_check": hashlib.sha256(os.urandom(16)).hexdigest()
        }

    def sign_attestation(self, payload: dict, priv_key_hex: str) -> dict:
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        if HAS_CRYPTO:
            priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(priv_key_hex))
            sig = priv.sign(bytes.fromhex(payload_hash)).hex()
        else:
            sig = hashlib.sha256(bytes.fromhex(priv_key_hex) + bytes.fromhex(payload_hash)).hexdigest()

        return {
            "payload": payload,
            "payload_hash": payload_hash,
            "signature": sig,
            "signature_type": "ed25519" if HAS_CRYPTO else "sha256-fallback"
        }
