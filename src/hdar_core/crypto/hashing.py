import hashlib
import hmac


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def secure_compare_hashes(h1: str, h2: str) -> bool:
    return hmac.compare_digest(h1.lower().encode(), h2.lower().encode())
