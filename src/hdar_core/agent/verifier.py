import hashlib
import sys
import importlib
from pathlib import Path
from hdar_core.crypto.ed25519 import verify_manifest_sig


class BaseVerifier:
    """Interface for pluggable state validation checks."""
    def verify(self, capsule_data: dict, dest_dir: Path) -> bool:
        raise NotImplementedError("Subclasses must implement verify")


class SignatureVerifier(BaseVerifier):
    """Verifies owner's Ed25519 signature on the capsule manifest."""
    def verify(self, capsule_data: dict, dest_dir: Path) -> bool:
        manifest = capsule_data.get("manifest")
        manifest_hash = capsule_data.get("manifest_hash")
        sig = capsule_data.get("signature")

        if not manifest or not manifest_hash or not sig:
            return False

        pub_hex = manifest.get("owner_public_key")
        if not pub_hex:
            return False

        return verify_manifest_sig(pub_hex, manifest_hash, sig)


class ChecksumVerifier(BaseVerifier):
    """Verifies that all extracted content matches their manifest hashes."""
    def verify(self, capsule_data: dict, dest_dir: Path) -> bool:
        manifest = capsule_data.get("manifest")
        if not manifest:
            return False

        files = manifest.get("files", {})
        for rel_path, expected_hash in files.items():
            file_path = dest_dir / rel_path
            if not file_path.exists():
                return False

            h = hashlib.sha256()
            with file_path.open("rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            actual_hash = h.hexdigest()

            if actual_hash != expected_hash:
                return False

        return True


class DependencyVerifier(BaseVerifier):
    """Verifies that required python modules are available in the runtime."""
    def __init__(self, required_modules: list[str] | None = None):
        self.required_modules = required_modules or ["json", "hashlib"]

    def verify(self, capsule_data: dict, dest_dir: Path) -> bool:
        for module in self.required_modules:
            try:
                importlib.import_module(module)
            except ImportError:
                return False
        return True
