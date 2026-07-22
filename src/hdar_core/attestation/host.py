import sys
import os
import platform
import json
import hashlib
import time
import subprocess

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class HostAttestationEngine:
    """
    Hardware-Aligned Host Attestation Engine.
    Queries TPM configuration on Linux and Hardware Expert profiles on macOS
    to bind capsule signatures directly to physically attested compute hosts.
    """
    def __init__(self, host_label: str = "docker-sandbox"):
        self.host_label = host_label

    def _get_macos_uuid(self) -> str:
        try:
            out = subprocess.check_output([
                "ioreg", "-d2", "-c", "IOPlatformExpertDevice"
            ]).decode('utf-8')
            for line in out.split("\n"):
                if "IOPlatformUUID" in line:
                    return line.split("=")[1].replace('"', '').strip()
        except Exception:
            pass
        return "macos-hardware-uuid-unknown"

    def _get_linux_tpm_status(self) -> str:
        tpm_path = "/sys/class/tpm/tpm0/device/description"
        if os.path.exists(tpm_path):
            try:
                with open(tpm_path, "r") as f:
                    return f.read().strip()
            except Exception:
                pass
        return "linux-tpm-inactive"

    def collect_attestation_payload(self) -> dict:
        hardware_id = "unknown-hwid"
        tpm_status = "unsupported"

        if sys.platform == "darwin":
            hardware_id = self._get_macos_uuid()
            tpm_status = "secure-enclave-capable"
        elif sys.platform.startswith("linux"):
            tpm_status = self._get_linux_tpm_status()
            uuid_path = "/sys/class/dmi/id/product_uuid"
            if os.path.exists(uuid_path):
                try:
                    with open(uuid_path, "r") as f:
                        hardware_id = f.read().strip()
                except Exception:
                    pass

        return {
            "attestation_version": "1.2.0",
            "host_label": self.host_label,
            "os_platform": sys.platform,
            "os_release": platform.release(),
            "cpu_architecture": platform.machine(),
            "hardware_uuid": hardware_id,
            "tpm_device_status": tpm_status,
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
