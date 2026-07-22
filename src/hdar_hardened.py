import os
import sys
import json
import hashlib
import hmac
import tarfile
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# Strict limits to defend against resource exhaustion & archive bombs
MAX_CAPSULE_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB limit
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024     # 100 MB limit per file
ALLOWED_PERMISSIONS_MASK = 0o755            # Strips SUID, SGID, and sticky bits


class HDARSafetyError(SecurityError if "SecurityError" in dir() else Exception):
    pass


def secure_compare_hashes(h1: str, h2: str) -> bool:
    """Uses constant-time comparison to prevent side-channel timing attacks."""
    return hmac.compare_digest(h1.lower().encode(), h2.lower().encode())


def safe_resolve_path(base_dir: Path, rel_path: str) -> Path:
    """
    Prevents Directory Traversal attacks.
    Ensures the target file path resides strictly inside the base directory.
    """
    resolved_base = base_dir.resolve()
    target_path = Path(base_dir, rel_path).resolve()
    
    # Enforce hierarchy bounds
    if not target_path.as_posix().startswith(resolved_base.as_posix()):
        raise HDARSafetyError(f"Directory Traversal Attack Blocked: {rel_path}")
    return target_path


def sanitize_permissions(mode: int) -> int:
    """Enforces strict mode mask, stripping SUID, SGID, and sticky bits."""
    return mode & ALLOWED_PERMISSIONS_MASK


def verify_capsule_limits(capsule_path: Path):
    """Protects against Zip/Archive Bomb attacks."""
    st = capsule_path.stat()
    if st.st_size > MAX_CAPSULE_SIZE_BYTES:
        raise HDARSafetyError(f"Capsule size exceeds safety limit of {MAX_CAPSULE_SIZE_BYTES} bytes.")


def safe_extract_tar(tar_path: Path, target_dir: Path):
    """
    Safely extracts tarball contents ensuring traversal checks,
    file size limit verification, and permission sanitization.
    """
    verify_capsule_limits(tar_path)
    resolved_target = target_dir.resolve()
    resolved_target.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_path, "r:gz") as tar:
        for member in tar.getmembers():
            # Validate size
            if member.size > MAX_FILE_SIZE_BYTES:
                raise HDARSafetyError(f"File {member.name} exceeds safety limit of {MAX_FILE_SIZE_BYTES} bytes.")
            
            # Prevent traversal via name
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise HDARSafetyError(f"Malformed path in capsule: {member.name}")
            
            # Safe path resolution
            if member.name.startswith("content/"):
                rel = member.name.replace("content/", "")
                out_path = safe_resolve_path(resolved_target, rel)
                
                # Sanitize permissions
                member.mode = sanitize_permissions(member.mode)
                
                # Extract
                out_path.parent.mkdir(parents=True, exist_ok=True)
                f_data = tar.extractfile(member)
                if f_data:
                    with open(out_path, "wb") as f:
                        f.write(f_data.read())
