from pathlib import Path


class HDARSafetyError(Exception):
    pass


def safe_resolve_path(base_dir: Path, rel_path: str) -> Path:
    resolved_base = base_dir.resolve()
    target_path = Path(base_dir, rel_path).resolve()
    if not target_path.as_posix().startswith(resolved_base.as_posix()):
        raise HDARSafetyError(f"Directory Traversal Attack Blocked: {rel_path}")
    return target_path
