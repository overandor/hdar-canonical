import json
import hashlib
from pathlib import Path
from hdar_core.crypto.hashing import sha256_file


def hash_workspace(workspace_dir: Path) -> tuple[str, dict]:
    file_map = {}
    root = Path(workspace_dir).resolve()
    for p in sorted(root.rglob('*')):
        if p.is_file() and not p.name.startswith('.git') and not p.name.endswith('.hdar') and not '.pytest_cache' in p.parts:
            rel = str(p.relative_to(root))
            file_map[rel] = sha256_file(p)
    manifest_str = json.dumps(file_map, sort_keys=True)
    root_hash = hashlib.sha256(manifest_str.encode('utf-8')).hexdigest()
    return root_hash, file_map
