ALLOWED_PERMISSIONS_MASK = 0o755


def sanitize_permissions(mode: int) -> int:
    return mode & ALLOWED_PERMISSIONS_MASK
