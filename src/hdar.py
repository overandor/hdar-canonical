"""HDAR canonical protocol library — single source of truth.

All other modules import from here. No duplicate function definitions.
No competing implementations. One schema, one capsule format, one task contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical constants — the only place these live
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "hdar/v1.0-canonical"
CAPSULE_SCHEMA = "hdar.transport-capsule/v1.0"
RECEIPT_SCHEMA = "hdar.receipt/v1.0"
REPORT_SCHEMA = "hdar.host-b-report/v1.0"
VERIFIER_SCHEMA = "hdar.verifier-report/v1.0"
AGENT_ID = "hdar-canonical-agent"
CHUNK_SIZE = 1024 * 1024


# ---------------------------------------------------------------------------
# Crypto — Ed25519 with hash-only fallback
# ---------------------------------------------------------------------------

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def generate_keypair() -> tuple[bytes, bytes]:
    if HAS_CRYPTO:
        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key()
        priv_bytes = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return priv_bytes, pub_bytes
    return b"hash-only-fallback-private", b"hash-only-fallback-public"


def sign_message(priv_bytes: bytes, message: bytes) -> bytes:
    if HAS_CRYPTO:
        priv = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        return priv.sign(message)
    return sha256_bytes(message + priv_bytes).encode()


def verify_signature(pub_bytes: bytes, message: bytes, signature: bytes) -> bool:
    if HAS_CRYPTO:
        try:
            pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
            pub.verify(signature, message)
            return True
        except Exception:
            return False
    expected = sha256_bytes(message + b"hash-only-fallback-private").encode()
    return expected == signature


# ---------------------------------------------------------------------------
# Hashing primitives — one implementation, imported everywhere
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(data: dict) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


# ---------------------------------------------------------------------------
# Workspace hashing — one implementation
# ---------------------------------------------------------------------------

def hash_workspace(workspace: Path) -> dict:
    files: list[dict] = []
    total_size = 0
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel_path = path.relative_to(workspace).as_posix()
        st = path.stat()
        entry = {
            "rel_path": rel_path,
            "sha256": sha256_file(path),
            "size": st.st_size,
            "mode": st.st_mode & 0o777,
        }
        files.append(entry)
        total_size += entry["size"]
    root_material = "\n".join(
        f"{f['rel_path']}|{f['sha256']}|{f['size']}|{f['mode']}" for f in files
    ).encode()
    return {
        "root_hash": sha256_bytes(root_material),
        "files": files,
        "total_size": total_size,
    }


# ---------------------------------------------------------------------------
# Capsule seal — one implementation, one schema
# ---------------------------------------------------------------------------

_EXCLUDE_FROM_HASH = {"manifest_hash", "owner_signature"}


def seal_workspace(
    workspace: Path,
    capsule_dir: Path,
    *,
    epoch: int,
    parent_manifest_hash: str | None,
    source_host_label: str,
    objective: str,
    continuation_point: str,
    owner_private_key: bytes | None = None,
    owner_public_key: bytes | None = None,
) -> dict:
    capsule_dir.mkdir(parents=True, exist_ok=True)
    blocks_dir = capsule_dir / "blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)

    workspace_manifest = hash_workspace(workspace)
    for entry in workspace_manifest["files"]:
        src = workspace / entry["rel_path"]
        digest = entry["sha256"]
        dest = blocks_dir / digest[:2] / digest
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    manifest: dict = {
        "schema": CAPSULE_SCHEMA,
        "protocol_version": PROTOCOL_VERSION,
        "agent_id": AGENT_ID,
        "epoch": epoch,
        "parent_manifest_hash": parent_manifest_hash,
        "created_at": time.time(),
        "source_host_label": source_host_label,
        "objective": objective,
        "continuation_point": continuation_point,
        "verification_mode": "sha256-content-addressed",
        "workspace_manifest": workspace_manifest,
    }

    if owner_public_key is not None:
        manifest["owner_signature_algorithm"] = "ed25519" if HAS_CRYPTO else "hash-only-fallback"
        manifest["owner_public_key"] = owner_public_key.hex()

    manifest["manifest_hash"] = sha256_bytes(
        canonical_json({k: v for k, v in manifest.items() if k not in _EXCLUDE_FROM_HASH})
    )

    if owner_private_key is not None and owner_public_key is not None:
        signature = sign_message(owner_private_key, manifest["manifest_hash"].encode())
        manifest["owner_signature"] = signature.hex()

    (capsule_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True)
    )

    receipt: dict = {
        "schema": RECEIPT_SCHEMA,
        "event": "capsule_sealed",
        "agent_id": AGENT_ID,
        "epoch": epoch,
        "source_host_label": source_host_label,
        "manifest_hash": manifest["manifest_hash"],
        "workspace_root_hash": workspace_manifest["root_hash"],
        "timestamp": time.time(),
        "platform": _platform_string(),
    }
    receipt["receipt_hash"] = sha256_bytes(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_hash"})
    )
    (capsule_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True)
    )
    return manifest


# ---------------------------------------------------------------------------
# Capsule verify — one implementation
# ---------------------------------------------------------------------------

def verify_capsule(capsule_dir: Path, owner_public_key: bytes | None = None) -> dict:
    manifest = json.loads((capsule_dir / "manifest.json").read_text())
    expected_hash = sha256_bytes(
        canonical_json({k: v for k, v in manifest.items() if k not in _EXCLUDE_FROM_HASH})
    )
    problems: list[str] = []
    if expected_hash != manifest.get("manifest_hash"):
        problems.append("manifest hash mismatch")

    missing = 0
    corrupt = 0
    for entry in manifest["workspace_manifest"]["files"]:
        digest = entry["sha256"]
        blob = capsule_dir / "blocks" / digest[:2] / digest
        if not blob.exists():
            missing += 1
        elif sha256_file(blob) != digest:
            corrupt += 1
    if missing:
        problems.append(f"{missing} content blocks missing")
    if corrupt:
        problems.append(f"{corrupt} content blocks corrupt")

    owner_signed = False
    signature_valid = False
    if "owner_signature" in manifest and "owner_public_key" in manifest:
        owner_signed = True
        if owner_public_key is not None:
            if manifest["owner_public_key"] == owner_public_key.hex():
                signature_valid = verify_signature(
                    owner_public_key,
                    manifest["manifest_hash"].encode(),
                    bytes.fromhex(manifest["owner_signature"]),
                )
                if not signature_valid:
                    problems.append("owner signature verification failed")
            else:
                problems.append("owner public key mismatch")
        else:
            signature_valid = True

    return {
        "ok": not problems,
        "problems": problems,
        "agent_id": manifest["agent_id"],
        "epoch": manifest["epoch"],
        "manifest_hash": manifest["manifest_hash"],
        "workspace_root_hash": manifest["workspace_manifest"]["root_hash"],
        "file_count": len(manifest["workspace_manifest"]["files"]),
        "total_size": manifest["workspace_manifest"]["total_size"],
        "owner_signed": owner_signed,
        "signature_valid": signature_valid,
        "parent_manifest_hash": manifest.get("parent_manifest_hash"),
        "protocol_version": manifest.get("protocol_version"),
    }


# ---------------------------------------------------------------------------
# Workspace restore — one implementation
# ---------------------------------------------------------------------------

def restore_workspace(capsule_dir: Path, dest: Path) -> dict:
    manifest = json.loads((capsule_dir / "manifest.json").read_text())
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for entry in manifest["workspace_manifest"]["files"]:
        blob = capsule_dir / "blocks" / entry["sha256"][:2] / entry["sha256"]
        out = dest / entry["rel_path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(blob, out)
        os.chmod(out, entry["mode"])
    restored = hash_workspace(dest)
    return {
        "restored_root_hash": restored["root_hash"],
        "expected_root_hash": manifest["workspace_manifest"]["root_hash"],
        "exact": restored["root_hash"] == manifest["workspace_manifest"]["root_hash"],
        "file_count": len(restored["files"]),
        "total_size": restored["total_size"],
    }


# ---------------------------------------------------------------------------
# Canonical task contract — the only task Host B knows how to execute
# ---------------------------------------------------------------------------

def execute_task(workspace: Path) -> dict:
    """5-stage deterministic pipeline. This is the canonical task contract.

    Stages: parse → filter → aggregate → classify → report
    Each stage hashes its output and chains to the next via parent_hash.
    """
    out = workspace / "output"
    out.mkdir(parents=True, exist_ok=True)

    # Stage 1: Parse
    input_path = workspace / "data" / "input_records.jsonl"
    records = [json.loads(l) for l in input_path.read_text().strip().split("\n") if l.strip()]
    pr = {
        "stage": "parse",
        "records_loaded": len(records),
        "first_id": records[0]["id"],
        "last_id": records[-1]["id"],
        "parent_hash": "0" * 64,
    }
    parse_hash = sha256_bytes(canonical_json(pr))
    pr["stage_hash"] = parse_hash
    (out / "stage_parse.json").write_text(json.dumps(pr, indent=2, sort_keys=True) + "\n")

    # Stage 2: Filter
    valid, rejected = [], []
    for r in records:
        if not r.get("id") or not r.get("category") or "value" not in r:
            rejected.append({"id": r.get("id", "unknown"), "reason": "missing_fields"})
        elif not isinstance(r["value"], (int, float)) or r["value"] < 0:
            rejected.append({"id": r["id"], "reason": "invalid_value"})
        else:
            valid.append(r)
    fr = {
        "stage": "filter",
        "parent_hash": parse_hash,
        "input_count": len(records),
        "valid_count": len(valid),
        "rejected_count": len(rejected),
        "rejected": rejected,
    }
    filter_hash = sha256_bytes(canonical_json(fr))
    fr["stage_hash"] = filter_hash
    (out / "stage_filter.json").write_text(json.dumps(fr, indent=2, sort_keys=True) + "\n")

    # Stage 3: Aggregate
    by_cat = defaultdict(list)
    for r in valid:
        by_cat[r["category"]].append(r["value"])
    stats = {}
    for cat, vals in sorted(by_cat.items()):
        stats[cat] = {
            "count": len(vals),
            "sum": round(sum(vals), 4),
            "mean": round(sum(vals) / len(vals), 4),
            "min": min(vals),
            "max": max(vals),
            "median": sorted(vals)[len(vals) // 2],
        }
    ar = {
        "stage": "aggregate",
        "parent_hash": filter_hash,
        "categories": list(sorted(by_cat.keys())),
        "stats": stats,
    }
    agg_hash = sha256_bytes(canonical_json(ar))
    ar["stage_hash"] = agg_hash
    (out / "stage_aggregate.json").write_text(json.dumps(ar, indent=2, sort_keys=True) + "\n")

    # Stage 4: Classify
    tiers = {"critical": [], "high": [], "medium": [], "low": []}
    for r in valid:
        cm = stats[r["category"]]["mean"]
        ratio = r["value"] / cm if cm > 0 else 0
        if ratio >= 2.0:
            tiers["critical"].append(r["id"])
        elif ratio >= 1.5:
            tiers["high"].append(r["id"])
        elif ratio >= 0.5:
            tiers["medium"].append(r["id"])
        else:
            tiers["low"].append(r["id"])
    cr = {
        "stage": "classify",
        "parent_hash": agg_hash,
        "tier_counts": {k: len(v) for k, v in tiers.items()},
        "tier_members": tiers,
    }
    classify_hash = sha256_bytes(canonical_json(cr))
    cr["stage_hash"] = classify_hash
    (out / "stage_classify.json").write_text(json.dumps(cr, indent=2, sort_keys=True) + "\n")

    # Stage 5: Report
    report = {
        "stage": "report",
        "parent_hash": classify_hash,
        "pipeline": "multi_stage_analysis_pipeline",
        "summary": {
            "total_input": pr["records_loaded"],
            "valid_records": fr["valid_count"],
            "rejected": fr["rejected_count"],
            "categories": ar["categories"],
            "tier_distribution": cr["tier_counts"],
        },
        "category_stats": stats,
        "tier_members": tiers,
        "metadata": {"stages_completed": 5, "version": "1.0"},
    }
    rh = sha256_bytes(canonical_json(report))
    report["stage_hash"] = rh
    (out / "final_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    return report


# ---------------------------------------------------------------------------
# Platform string — one implementation
# ---------------------------------------------------------------------------

def _platform_string() -> str:
    import platform
    return platform.platform()


# ---------------------------------------------------------------------------
# Safe tar extraction
# ---------------------------------------------------------------------------

def safe_extract_tar(tf, dest: Path) -> None:
    try:
        tf.extractall(dest, filter="data")
    except TypeError:
        tf.extractall(dest)
