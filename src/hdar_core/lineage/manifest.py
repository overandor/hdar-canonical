import json
import hashlib
import time


def create_manifest(epoch: int, parent_hash: str | None, root_hash: str, pub_hex: str, file_map: dict) -> tuple[dict, str]:
    manifest = {
        "hdar_version": "1.2.0",
        "epoch": epoch,
        "parent_manifest_hash": parent_hash or "0000000000000000000000000000000000000000000000000000000000000000",
        "content_merkle_root": root_hash,
        "owner_public_key": pub_hex,
        "timestamp": time.time(),
        "files": file_map
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode('utf-8')
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    return manifest, manifest_hash
