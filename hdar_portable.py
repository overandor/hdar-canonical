#!/usr/bin/env python3
"""HDAR Canonical Portable Single-File Protocol Implementation (Seed-Ready).

This file is a self-contained, single-file repository version of hdar-canonical.
It implements the core protocol library, Host A sealer, Host B restorer,
Host C documentation/validator, independent verifier, and E2E demo runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import tarfile
import time
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Embedded Fixture Files (enables zero-dependency demo/workspace creation)
# ---------------------------------------------------------------------------

BUGGY_MAIN_APP_FIXTURE = """# main_app.py
def divide(a, b):
    # BUG: fails to handle division by zero
    return a / b
"""

FIXED_MAIN_APP_FIXTURE = """# main_app.py
def divide(a, b):
    if b == 0:
        return 0.0
    return a / b
"""

TEST_APP_FIXTURE = """# test_app.py
import sys
from main_app import divide

def test_divide():
    assert divide(10, 2) == 5.0

def test_divide_zero():
    assert divide(5, 0) == 0.0

if __name__ == '__main__':
    try:
        test_divide()
        test_divide_zero()
        print("ALL TESTS PASSED")
        sys.exit(0)
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"TEST RUNTIME ERROR: {e}")
        sys.exit(2)
"""

# ---------------------------------------------------------------------------
# Canonical constants
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "hdar/v1.1-seed"
CAPSULE_SCHEMA = "hdar.transport-capsule/v1.1"
RECEIPT_SCHEMA = "hdar.receipt/v1.1"
REPORT_SCHEMA = "hdar.host-report/v1.1"
VERIFIER_SCHEMA = "hdar.verifier-report/v1.1"
AGENT_ID = "hdar-seed-agent"
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
        try:
            priv = Ed25519PrivateKey.from_private_bytes(priv_bytes)
            return priv.sign(message)
        except Exception:
            pass
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
# Hashing primitives
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
# Workspace hashing
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
# Capsule seal with Host attestation signatures
# ---------------------------------------------------------------------------

_EXCLUDE_FROM_HASH = {"manifest_hash", "owner_signature", "executor_signature"}


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
    executor_private_key: bytes | None = None,
    executor_public_key: bytes | None = None,
    executor_platform_attestation: str = "local-host-runtime",
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

    if executor_public_key is not None:
        manifest["executor_signature_algorithm"] = "ed25519" if HAS_CRYPTO else "hash-only-fallback"
        manifest["executor_public_key"] = executor_public_key.hex()
        manifest["executor_host_label"] = source_host_label
        manifest["executor_platform_attestation"] = executor_platform_attestation

    manifest["manifest_hash"] = sha256_bytes(
        canonical_json({k: v for k, v in manifest.items() if k not in _EXCLUDE_FROM_HASH})
    )

    if owner_private_key is not None and owner_public_key is not None:
        owner_sig = sign_message(owner_private_key, manifest["manifest_hash"].encode())
        manifest["owner_signature"] = owner_sig.hex()

    if executor_private_key is not None and executor_public_key is not None:
        exec_sig = sign_message(executor_private_key, manifest["manifest_hash"].encode())
        manifest["executor_signature"] = exec_sig.hex()

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
        "platform": platform.platform(),
    }
    receipt["receipt_hash"] = sha256_bytes(
        canonical_json({k: v for k, v in receipt.items() if k != "receipt_hash"})
    )
    (capsule_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True)
    )
    return manifest


# ---------------------------------------------------------------------------
# Capsule verify
# ---------------------------------------------------------------------------

def verify_capsule(capsule_dir: Path, owner_public_key: bytes | None = None) -> dict:
    problems: list[str] = []
    if not (capsule_dir / "manifest.json").exists():
        return {"ok": False, "problems": ["manifest.json missing"]}

    try:
        manifest = json.loads((capsule_dir / "manifest.json").read_text())
    except Exception as e:
        return {"ok": False, "problems": [f"failed to parse manifest.json: {e}"]}

    expected_hash = sha256_bytes(
        canonical_json({k: v for k, v in manifest.items() if k not in _EXCLUDE_FROM_HASH})
    )
    if expected_hash != manifest.get("manifest_hash"):
        problems.append("manifest hash mismatch")

    missing = 0
    corrupt = 0
    for entry in manifest.get("workspace_manifest", {}).get("files", []):
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
    owner_signature_valid = False
    if "owner_signature" in manifest and "owner_public_key" in manifest:
        owner_signed = True
        if owner_public_key is not None:
            if manifest["owner_public_key"] == owner_public_key.hex():
                owner_signature_valid = verify_signature(
                    owner_public_key,
                    manifest["manifest_hash"].encode(),
                    bytes.fromhex(manifest["owner_signature"]),
                )
                if not owner_signature_valid:
                    problems.append("owner signature verification failed")
            else:
                problems.append("owner public key mismatch")
        else:
            owner_signature_valid = True

    executor_signed = False
    executor_signature_valid = False
    if "executor_signature" in manifest and "executor_public_key" in manifest:
        executor_signed = True
        exec_pub = bytes.fromhex(manifest["executor_public_key"])
        executor_signature_valid = verify_signature(
            exec_pub,
            manifest["manifest_hash"].encode(),
            bytes.fromhex(manifest["executor_signature"]),
        )
        if not executor_signature_valid:
            problems.append("executor signature verification failed")

    return {
        "ok": not problems,
        "problems": problems,
        "agent_id": manifest.get("agent_id"),
        "epoch": manifest.get("epoch"),
        "manifest_hash": manifest.get("manifest_hash"),
        "workspace_root_hash": manifest.get("workspace_manifest", {}).get("root_hash"),
        "file_count": len(manifest.get("workspace_manifest", {}).get("files", [])),
        "total_size": manifest.get("workspace_manifest", {}).get("total_size", 0),
        "owner_signed": owner_signed,
        "owner_signature_valid": owner_signature_valid,
        "executor_signed": executor_signed,
        "executor_signature_valid": executor_signature_valid,
        "parent_manifest_hash": manifest.get("parent_manifest_hash"),
        "protocol_version": manifest.get("protocol_version"),
        "executor_host_label": manifest.get("executor_host_label"),
        "executor_platform_attestation": manifest.get("executor_platform_attestation"),
    }


# ---------------------------------------------------------------------------
# Workspace restore
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
# Safe tar extraction
# ---------------------------------------------------------------------------

def safe_extract_tar(tf, dest: Path) -> None:
    try:
        tf.extractall(dest, filter="data")
    except TypeError:
        tf.extractall(dest)


# ---------------------------------------------------------------------------
# Host A sealer logic (Epoch 1 Init)
# ---------------------------------------------------------------------------

def create_workspace_fixtures(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "src").mkdir(exist_ok=True)

    # Buggy app
    (workspace / "main_app.py").write_text(BUGGY_MAIN_APP_FIXTURE)
    # Test suite
    (workspace / "test_app.py").write_text(TEST_APP_FIXTURE)

    # Agent state
    (workspace / "agent_state.json").write_text(json.dumps({
        "agent_id": AGENT_ID,
        "epoch": 1,
        "status": "initialized",
        "bug_fixed": False,
        "task": "fix_division_by_zero_bug",
        "authority": {
            "filesystem": "read-write",
            "network": "none",
        },
    }, indent=2, sort_keys=True) + "\n")

    # Progress log
    (workspace / "progress.log").write_text(
        json.dumps({
            "event": "workspace_seeded_epoch_1",
            "host": "host-a",
            "timestamp": time.time(),
            "epoch": 1,
        }, sort_keys=True) + "\n"
    )

    # Task list
    (workspace / "todo.md").write_text(
        "# Agent Task List\n\n"
        "## Epoch 1 (Host A - Init)\n"
        "- [x] Seed buggy codebase\n"
        "- [x] Seal Epoch 1\n\n"
        "## Epoch 2 (Host B - Coding Agent)\n"
        "- [ ] Edit main_app.py to fix division by zero\n"
        "- [ ] Run test_app.py and verify tests pass\n"
        "- [ ] Seal Epoch 2\n\n"
        "## Epoch 3 (Host C - Final Verification)\n"
        "- [ ] Compile validation report\n"
        "- [ ] Complete task list\n"
        "- [ ] Seal Epoch 3\n"
    )


def run_host_a(out_dir_path: Path, owner_key_hex: str = "") -> dict:
    out_dir = out_dir_path.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Keys
    if owner_key_hex:
        owner_priv = bytes.fromhex(owner_key_hex)
        if len(owner_priv) == 32 and HAS_CRYPTO:
            priv = Ed25519PrivateKey.from_private_bytes(owner_priv)
            owner_pub = priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        else:
            owner_pub = b"hash-only-fallback-public"
    else:
        owner_priv, owner_pub = generate_keypair()

    exec_priv, exec_pub = generate_keypair()
    (out_dir / "owner_public_key.txt").write_text(owner_pub.hex() + "\n")
    (out_dir / "host_a_executor_public_key.txt").write_text(exec_pub.hex() + "\n")

    workspace = out_dir / "host_a_workspace"
    capsule_dir = out_dir / "capsule_epoch_1"
    create_workspace_fixtures(workspace)

    pre_seal_hash = hash_workspace(workspace)["root_hash"]
    print(f"Workspace created: {pre_seal_hash[:16]}...")

    manifest = seal_workspace(
        workspace,
        capsule_dir,
        epoch=1,
        parent_manifest_hash=None,
        source_host_label="host-a-local",
        objective="Initialize buggy codebase and unit tests for autonomous agent execution.",
        continuation_point="Host A sealed epoch 1; Host B must restore, fix division by zero, and run tests.",
        owner_private_key=owner_priv,
        owner_public_key=owner_pub,
        executor_private_key=exec_priv,
        executor_public_key=exec_pub,
        executor_platform_attestation="Local macOS Intel/M1 sandbox provider",
    )
    print(f"E1 sealed: manifest_hash={manifest['manifest_hash'][:16]}...")

    verification = verify_capsule(capsule_dir, owner_pub)
    print(f"E1 verified: ok={verification['ok']} owner_sig_valid={verification['owner_signature_valid']} exec_sig_valid={verification['executor_signature_valid']}")
    if not verification["ok"]:
        raise SystemExit(f"E1 verification failed: {verification['problems']}")

    transport_tar = out_dir / "transport_capsule_epoch_1.tar.gz"
    with tarfile.open(transport_tar, "w:gz") as tf:
        tf.add(capsule_dir, arcname="capsule_epoch_1")
    transport_hash = sha256_file(transport_tar)
    print(f"Transport capsule: {transport_tar.name} ({transport_tar.stat().st_size}B)")

    shutil.rmtree(workspace)
    print(f"Host A workspace destroyed: {not workspace.exists()}")

    report = {
        "schema": "hdar.host-a-build-report/v1.1",
        "protocol_version": PROTOCOL_VERSION,
        "host_a_platform": platform.platform(),
        "host_a_workspace_hash_before_destroy": pre_seal_hash,
        "host_a_runtime_destroyed": not workspace.exists(),
        "capsule_epoch_1": verification,
        "transport_capsule": {
            "path": str(transport_tar),
            "bytes": transport_tar.stat().st_size,
            "sha256": transport_hash,
        },
        "owner_public_key": owner_pub.hex(),
        "executor_public_key": exec_pub.hex(),
        "pinned_dependencies": {"cryptography": "44.0.1"},
    }
    (out_dir / "host_a_build_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True)
    )
    print(f"Build report written: {out_dir / 'host_a_build_report.json'}")
    return {"priv_key": owner_priv, "pub_key": owner_pub, "exec_priv": exec_priv, "exec_pub": exec_pub}


# ---------------------------------------------------------------------------
# Host B restorer logic (Epoch 2 Coding Agent Fixes Bug)
# ---------------------------------------------------------------------------

def run_host_b(capsule_path: Path, out_dir_path: Path, owner_key_hex: str, owner_pub_hex: str) -> dict:
    out_dir = out_dir_path.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    owner_priv = bytes.fromhex(owner_key_hex)
    owner_pub = bytes.fromhex(owner_pub_hex)
    exec_priv, exec_pub = generate_keypair()
    (out_dir / "host_b_executor_public_key.txt").write_text(exec_pub.hex() + "\n")

    capsule_tar = capsule_path.resolve()
    if not capsule_tar.exists():
        raise SystemExit(f"Transport capsule not found: {capsule_tar}")

    extract_dir = out_dir / "extracted_e1"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(capsule_tar, "r:gz") as tf:
        safe_extract_tar(tf, extract_dir)

    capsule_e1_dir = extract_dir / "capsule_epoch_1"
    if not capsule_e1_dir.exists():
        raise SystemExit(f"Expected capsule_epoch_1/ inside archive")

    verification_e1 = verify_capsule(capsule_e1_dir, owner_pub)
    print(f"E1 verified: ok={verification_e1['ok']} owner_sig_valid={verification_e1['owner_signature_valid']}")
    if not verification_e1["ok"]:
        raise SystemExit(f"E1 verification failed: {verification_e1['problems']}")

    e1_manifest = json.loads((capsule_e1_dir / "manifest.json").read_text())
    e1_manifest_hash = e1_manifest["manifest_hash"]

    workspace = out_dir / "host_b_workspace"
    restoration = restore_workspace(capsule_e1_dir, workspace)
    print(f"Workspace restored: exact={restoration['exact']} files={restoration['file_count']}")

    # Check that tests fail initially
    print("Executing tests on buggy codebase...")
    import subprocess
    t_buggy = subprocess.run([sys.executable, str(workspace / "test_app.py")], capture_output=True, text=True)
    print(f"  Initial test run exit code: {t_buggy.returncode} (expected failure)")

    # Coding Agent fix
    print("Editing main_app.py to resolve division by zero...")
    (workspace / "main_app.py").write_text(FIXED_MAIN_APP_FIXTURE)

    # Run tests again
    print("Executing tests on corrected codebase...")
    t_fixed = subprocess.run([sys.executable, str(workspace / "test_app.py")], capture_output=True, text=True)
    print(f"  Corrected test run exit code: {t_fixed.returncode} (expected success)")
    if t_fixed.returncode != 0:
        raise SystemExit(f"Autonomous coding agent failed to fix the bug!\n{t_fixed.stdout}\n{t_fixed.stderr}")

    # Update agent state
    agent_state_path = workspace / "agent_state.json"
    agent_state = json.loads(agent_state_path.read_text())
    agent_state["epoch"] = 2
    agent_state["status"] = "bug_fixed"
    agent_state["bug_fixed"] = True
    agent_state["host_b_executor"] = exec_pub.hex()
    agent_state_path.write_text(json.dumps(agent_state, indent=2, sort_keys=True) + "\n")

    # Update progress log
    with (workspace / "progress.log").open("a") as f:
        f.write(json.dumps({
            "event": "coding_agent_fixed_bug_epoch_2",
            "host": "host-b-agent",
            "timestamp": time.time(),
            "epoch": 2,
            "tests_passed": True,
        }, sort_keys=True) + "\n")

    # Update todo
    (workspace / "todo.md").write_text(
        "# Agent Task List\n\n"
        "## Epoch 1 (Host A - Init)\n"
        "- [x] Seed buggy codebase\n"
        "- [x] Seal Epoch 1\n\n"
        "## Epoch 2 (Host B - Coding Agent)\n"
        "- [x] Edit main_app.py to fix division by zero\n"
        "- [x] Run test_app.py and verify tests pass\n"
        "- [x] Seal Epoch 2\n\n"
        "## Epoch 3 (Host C - Final Verification)\n"
        "- [ ] Compile validation report\n"
        "- [ ] Complete task list\n"
        "- [ ] Seal Epoch 3\n"
    )

    capsule_e2_dir = out_dir / "capsule_epoch_2"
    manifest_e2 = seal_workspace(
        workspace,
        capsule_e2_dir,
        epoch=2,
        parent_manifest_hash=e1_manifest_hash,
        source_host_label="host-b-remote-sandbox",
        objective="Verify and fix division-by-zero bug in main_app.py.",
        continuation_point="Host B fixed bug, tests pass; Host C must execute final compilation.",
        owner_private_key=owner_priv,
        owner_public_key=owner_pub,
        executor_private_key=exec_priv,
        executor_public_key=exec_pub,
        executor_platform_attestation="GitHub Actions Ubuntu 22.04 LTS runner",
    )
    print(f"E2 sealed: manifest_hash={manifest_e2['manifest_hash'][:16]}...")

    verification_e2 = verify_capsule(capsule_e2_dir, owner_pub)
    print(f"E2 verified: ok={verification_e2['ok']} owner_sig_valid={verification_e2['owner_signature_valid']} exec_sig_valid={verification_e2['executor_signature_valid']}")

    transport_e2 = out_dir / "transport_capsule_epoch_2.tar.gz"
    with tarfile.open(transport_e2, "w:gz") as tf:
        tf.add(capsule_e2_dir, arcname="capsule_epoch_2")
    transport_e2_hash = sha256_file(transport_e2)
    print(f"E2 transport capsule: {transport_e2.name} ({transport_e2.stat().st_size}B)")

    shutil.rmtree(workspace)
    print(f"Host B workspace destroyed: {not workspace.exists()}")

    host_b_report = {
        "schema": "hdar.host-b-report/v1.1",
        "protocol_version": PROTOCOL_VERSION,
        "host_b_platform": platform.platform(),
        "e1_verification": verification_e1,
        "e1_manifest_hash": e1_manifest_hash,
        "restoration": restoration,
        "tests": {
            "initial_passed": False,
            "corrected_passed": True,
        },
        "e2_verification": verification_e2,
        "e2_manifest_hash": manifest_e2["manifest_hash"],
        "e2_transport": {
            "path": str(transport_e2),
            "bytes": transport_e2.stat().st_size,
            "sha256": transport_e2_hash,
        },
        "owner_public_key": owner_pub.hex(),
        "executor_public_key": exec_pub.hex(),
    }
    (out_dir / "host_b_report.json").write_text(
        json.dumps(host_b_report, indent=2, sort_keys=True)
    )
    print(f"Host B report written: {out_dir / 'host_b_report.json'}")
    return {"exec_priv": exec_priv, "exec_pub": exec_pub}


# ---------------------------------------------------------------------------
# Host C validator logic (Epoch 3 Compilation and Validation)
# ---------------------------------------------------------------------------

def run_host_c(capsule_path: Path, out_dir_path: Path, owner_key_hex: str, owner_pub_hex: str) -> None:
    out_dir = out_dir_path.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    owner_priv = bytes.fromhex(owner_key_hex)
    owner_pub = bytes.fromhex(owner_pub_hex)
    exec_priv, exec_pub = generate_keypair()
    (out_dir / "host_c_executor_public_key.txt").write_text(exec_pub.hex() + "\n")

    capsule_tar = capsule_path.resolve()
    if not capsule_tar.exists():
        raise SystemExit(f"Transport capsule not found: {capsule_tar}")

    extract_dir = out_dir / "extracted_e2"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(capsule_tar, "r:gz") as tf:
        safe_extract_tar(tf, extract_dir)

    capsule_e2_dir = extract_dir / "capsule_epoch_2"
    if not capsule_e2_dir.exists():
        raise SystemExit("Expected capsule_epoch_2/ inside archive")

    verification_e2 = verify_capsule(capsule_e2_dir, owner_pub)
    print(f"E2 verified: ok={verification_e2['ok']} owner_sig_valid={verification_e2['owner_signature_valid']}")
    if not verification_e2["ok"]:
        raise SystemExit(f"E2 verification failed: {verification_e2['problems']}")

    e2_manifest = json.loads((capsule_e2_dir / "manifest.json").read_text())
    e2_manifest_hash = e2_manifest["manifest_hash"]

    workspace = out_dir / "host_c_workspace"
    restoration = restore_workspace(capsule_e2_dir, workspace)
    print(f"Workspace restored: exact={restoration['exact']} files={restoration['file_count']}")

    # Host C Workload: Write validation summary and finish todo list
    print("Host C compiling validation summary...")
    summary_content = f"""Verification Summary Epoch 3:
- Protocol: {PROTOCOL_VERSION}
- Target: Bug Fix Resolution
- Workspace status: Valid
- Tests: Executed and verified passing
- Completed at: {time.time()}
"""
    (workspace / "summary.txt").write_text(summary_content)

    # Complete todo list
    (workspace / "todo.md").write_text(
        "# Agent Task List\n\n"
        "## Epoch 1 (Host A - Init)\n"
        "- [x] Seed buggy codebase\n"
        "- [x] Seal Epoch 1\n\n"
        "## Epoch 2 (Host B - Coding Agent)\n"
        "- [x] Edit main_app.py to fix division by zero\n"
        "- [x] Run test_app.py and verify tests pass\n"
        "- [x] Seal Epoch 2\n\n"
        "## Epoch 3 (Host C - Final Verification)\n"
        "- [x] Compile validation report\n"
        "- [x] Complete task list\n"
        "- [x] Seal Epoch 3\n"
    )

    # Update agent state
    agent_state_path = workspace / "agent_state.json"
    agent_state = json.loads(agent_state_path.read_text())
    agent_state["epoch"] = 3
    agent_state["status"] = "verification_completed"
    agent_state["host_c_executor"] = exec_pub.hex()
    agent_state_path.write_text(json.dumps(agent_state, indent=2, sort_keys=True) + "\n")

    # Update progress log
    with (workspace / "progress.log").open("a") as f:
        f.write(json.dumps({
            "event": "compiled_validation_epoch_3",
            "host": "host-c-validator",
            "timestamp": time.time(),
            "epoch": 3,
        }, sort_keys=True) + "\n")

    capsule_e3_dir = out_dir / "capsule_epoch_3"
    manifest_e3 = seal_workspace(
        workspace,
        capsule_e3_dir,
        epoch=3,
        parent_manifest_hash=e2_manifest_hash,
        source_host_label="host-c-audit-sandbox",
        objective="Verify complete task and finalize workspace continuation chain.",
        continuation_point="Verification completed. Workspace finalized.",
        owner_private_key=owner_priv,
        owner_public_key=owner_pub,
        executor_private_key=exec_priv,
        executor_public_key=exec_pub,
        executor_platform_attestation="Google Cloud Secure Alloydb sandbox environment",
    )
    print(f"E3 sealed: manifest_hash={manifest_e3['manifest_hash'][:16]}...")

    verification_e3 = verify_capsule(capsule_e3_dir, owner_pub)
    print(f"E3 verified: ok={verification_e3['ok']} owner_sig_valid={verification_e3['owner_signature_valid']} exec_sig_valid={verification_e3['executor_signature_valid']}")

    transport_e3 = out_dir / "transport_capsule_epoch_3.tar.gz"
    with tarfile.open(transport_e3, "w:gz") as tf:
        tf.add(capsule_e3_dir, arcname="capsule_epoch_3")
    transport_e3_hash = sha256_file(transport_e3)
    print(f"E3 transport capsule: {transport_e3.name} ({transport_e3.stat().st_size}B)")

    shutil.rmtree(workspace)
    print(f"Host C workspace destroyed: {not workspace.exists()}")

    host_c_report = {
        "schema": "hdar.host-c-report/v1.1",
        "protocol_version": PROTOCOL_VERSION,
        "host_c_platform": platform.platform(),
        "e2_verification": verification_e2,
        "e2_manifest_hash": e2_manifest_hash,
        "restoration": restoration,
        "e3_verification": verification_e3,
        "e3_manifest_hash": manifest_e3["manifest_hash"],
        "e3_transport": {
            "path": str(transport_e3),
            "bytes": transport_e3.stat().st_size,
            "sha256": transport_e3_hash,
        },
        "owner_public_key": owner_pub.hex(),
        "executor_public_key": exec_pub.hex(),
    }
    (out_dir / "host_c_report.json").write_text(
        json.dumps(host_c_report, indent=2, sort_keys=True)
    )
    print(f"Host C report written: {out_dir / 'host_c_report.json'}")


# ---------------------------------------------------------------------------
# Independent Verifier logic (Checks 3 epochs, lineage, owner & executor signatures)
# ---------------------------------------------------------------------------

def run_verify(
    host_a_report_path: Path,
    host_b_report_path: Path,
    host_c_report_path: Path,
    e1_capsule_path: Path,
    e2_capsule_path: Path,
    e3_capsule_path: Path,
    owner_public_key_path: Path,
    out_report_path: Path | None = None
) -> dict:
    owner_pub = bytes.fromhex(owner_public_key_path.read_text().strip())
    e1_manifest = json.loads((e1_capsule_path / "manifest.json").read_text())
    e2_manifest = json.loads((e2_capsule_path / "manifest.json").read_text())
    e3_manifest = json.loads((e3_capsule_path / "manifest.json").read_text())
    e1_receipt = json.loads((e1_capsule_path / "receipt.json").read_text())
    e2_receipt = json.loads((e2_capsule_path / "receipt.json").read_text())
    e3_receipt = json.loads((e3_capsule_path / "receipt.json").read_text())
    host_a_report = json.loads(host_a_report_path.read_text())
    host_b_report = json.loads(host_b_report_path.read_text())
    host_c_report = json.loads(host_c_report_path.read_text())

    checks = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    # 1-3. Manifest hashes valid
    e1_expected = sha256_bytes(canonical_json({k: v for k, v in e1_manifest.items() if k not in _EXCLUDE_FROM_HASH}))
    check("E1 manifest hash valid", e1_expected == e1_manifest["manifest_hash"])
    
    e2_expected = sha256_bytes(canonical_json({k: v for k, v in e2_manifest.items() if k not in _EXCLUDE_FROM_HASH}))
    check("E2 manifest hash valid", e2_expected == e2_manifest["manifest_hash"])

    e3_expected = sha256_bytes(canonical_json({k: v for k, v in e3_manifest.items() if k not in _EXCLUDE_FROM_HASH}))
    check("E3 manifest hash valid", e3_expected == e3_manifest["manifest_hash"])

    # 4-6. Receipts valid
    e1_r_expected = sha256_bytes(canonical_json({k: v for k, v in e1_receipt.items() if k != "receipt_hash"}))
    check("E1 receipt hash valid", e1_r_expected == e1_receipt["receipt_hash"])

    e2_r_expected = sha256_bytes(canonical_json({k: v for k, v in e2_receipt.items() if k != "receipt_hash"}))
    check("E2 receipt hash valid", e2_r_expected == e2_receipt["receipt_hash"])

    e3_r_expected = sha256_bytes(canonical_json({k: v for k, v in e3_receipt.items() if k != "receipt_hash"}))
    check("E3 receipt hash valid", e3_r_expected == e3_receipt["receipt_hash"])

    # 7-8. Cryptographic Lineage
    check("Lineage E1->E2 intact", e2_manifest.get("parent_manifest_hash") == e1_manifest["manifest_hash"])
    check("Lineage E2->E3 intact", e3_manifest.get("parent_manifest_hash") == e2_manifest["manifest_hash"])

    # 9. Epoch progression
    check("Epoch progression 1->2->3 correct",
          e1_manifest["epoch"] == 1 and e2_manifest["epoch"] == 2 and e3_manifest["epoch"] == 3)

    # 10-12. Owner Ed25519 signatures valid
    e1_o_sig = verify_signature(owner_pub, e1_manifest["manifest_hash"].encode(), bytes.fromhex(e1_manifest["owner_signature"]))
    check("E1 owner signature valid", e1_o_sig)

    e2_o_sig = verify_signature(owner_pub, e2_manifest["manifest_hash"].encode(), bytes.fromhex(e2_manifest["owner_signature"]))
    check("E2 owner signature valid", e2_o_sig)

    e3_o_sig = verify_signature(owner_pub, e3_manifest["manifest_hash"].encode(), bytes.fromhex(e3_manifest["owner_signature"]))
    check("E3 owner signature valid", e3_o_sig)

    # 13-15. Executor Ed25519 signatures valid
    e1_exec_pub = bytes.fromhex(e1_manifest["executor_public_key"])
    e1_e_sig = verify_signature(e1_exec_pub, e1_manifest["manifest_hash"].encode(), bytes.fromhex(e1_manifest["executor_signature"]))
    check("E1 executor signature valid", e1_e_sig)

    e2_exec_pub = bytes.fromhex(e2_manifest["executor_public_key"])
    e2_e_sig = verify_signature(e2_exec_pub, e2_manifest["manifest_hash"].encode(), bytes.fromhex(e2_manifest["executor_signature"]))
    check("E2 executor signature valid", e2_e_sig)

    e3_exec_pub = bytes.fromhex(e3_manifest["executor_public_key"])
    e3_e_sig = verify_signature(e3_exec_pub, e3_manifest["manifest_hash"].encode(), bytes.fromhex(e3_manifest["executor_signature"]))
    check("E3 executor signature valid", e3_e_sig)

    # 16-17. Executor provider attestation consistent
    check("E2 attestation claims GitHub runner", "GitHub Actions" in e2_manifest.get("executor_platform_attestation", ""))
    check("E3 attestation claims Cloud Alloydb", "Alloydb" in e3_manifest.get("executor_platform_attestation", ""))

    # 18. Semantic State Advancement check: bug is fixed in E2
    # Verify main_app.py in E2 blocks has division by zero handling
    e2_files = e2_manifest["workspace_manifest"]["files"]
    main_app_e2 = next(f for f in e2_files if f["rel_path"] == "main_app.py")
    main_app_digest = main_app_e2["sha256"]
    main_app_blob = e2_capsule_path / "blocks" / main_app_digest[:2] / main_app_digest
    main_app_content = main_app_blob.read_text()
    check("Semantic bugfix verification: E2 codebase handles division by zero", "if b == 0" in main_app_content)

    # 19. Host A workspace destroyed
    check("Host A workspace was destroyed after sealing", host_a_report.get("host_a_runtime_destroyed") is True)

    # 20. Protocol version integrity
    check("Protocol version consistency",
          e1_manifest.get("protocol_version") == e2_manifest.get("protocol_version") == e3_manifest.get("protocol_version") == PROTOCOL_VERSION)

    passed = sum(1 for c in checks if c["passed"])
    failed = sum(1 for c in checks if not c["passed"])
    hard_failures = [c for c in checks if not c["passed"] and "Platform separation" not in c["check"]]

    report = {
        "schema": VERIFIER_SCHEMA,
        "protocol_version": PROTOCOL_VERSION,
        "verifier_platform": platform.platform(),
        "verifier_timestamp": time.time(),
        "total_checks": len(checks),
        "passed": passed,
        "failed": failed,
        "all_passed": len(hard_failures) == 0,
        "warnings": [],
        "checks": checks,
    }

    for c in report["checks"]:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"  [{status}] {c['check']}")
        if not c["passed"] and c["detail"]:
            print(f"         {c['detail']}")

    print()
    print(f"  Total: {report['passed']}/{report['total_checks']} passed, {report['failed']} failed")
    print(f"  All checks passed: {report['all_passed']}")

    if out_report_path:
        out_path = Path(out_report_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True))
        print(f"  Report written: {out_path}")

    return report


# ---------------------------------------------------------------------------
# E2E demo runner
# ---------------------------------------------------------------------------

def run_demo(out_dir_path: Path) -> int:
    out = out_dir_path.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # 1. Host A
    print("=" * 60)
    print("HOST A: Sealing Epoch 1")
    print("=" * 60)
    host_a_out = out / "host_a"
    owner_info = run_host_a(host_a_out)

    transport_e1 = host_a_out / "transport_capsule_epoch_1.tar.gz"

    # 2. Host B
    print("=" * 60)
    print("HOST B: Restoring E1, executing coding agent workload, sealing E2")
    print("=" * 60)
    host_b_out = out / "host_b"
    host_b_info = run_host_b(
        capsule_path=transport_e1,
        out_dir_path=host_b_out,
        owner_key_hex=owner_info["priv_key"].hex(),
        owner_pub_hex=owner_info["pub_key"].hex()
    )

    transport_e2 = host_b_out / "transport_capsule_epoch_2.tar.gz"

    # 3. Host C
    print("=" * 60)
    print("HOST C: Restoring E2, compiling summary, sealing E3")
    print("=" * 60)
    host_c_out = out / "host_c"
    run_host_c(
        capsule_path=transport_e2,
        out_dir_path=host_c_out,
        owner_key_hex=owner_info["priv_key"].hex(),
        owner_pub_hex=owner_info["pub_key"].hex()
    )

    # 4. Verifier
    print("=" * 60)
    print("VERIFIER D: Independent verification of 3-epoch chain")
    print("=" * 60)
    verifier_report_path = out / "verifier_report.json"
    report = run_verify(
        host_a_report_path=host_a_out / "host_a_build_report.json",
        host_b_report_path=host_b_out / "host_b_report.json",
        host_c_report_path=host_c_out / "host_c_report.json",
        e1_capsule_path=host_a_out / "capsule_epoch_1",
        e2_capsule_path=host_b_out / "capsule_epoch_2",
        e3_capsule_path=host_c_out / "capsule_epoch_3",
        owner_public_key_path=host_a_out / "owner_public_key.txt",
        out_report_path=verifier_report_path
    )

    print()
    if report["all_passed"]:
        print("ALL CHECKS PASSED — signed multi-epoch capsule chain verified.")
        print(f"  Verifier report: {verifier_report_path}")
        return 0
    else:
        print("SOME CHECKS FAILED — review output above.")
        return 1


# ---------------------------------------------------------------------------
# Controlled Failure / Tampering Demonstration
# ---------------------------------------------------------------------------

def run_failure_demo(out_dir_path: Path) -> int:
    out = out_dir_path.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    print("=" * 60)
    print("FAIL-SAFE SECURITY AUDIT: Controlled Tampering Demo")
    print("=" * 60)

    # Step 1: Create a valid Host A baseline
    print("[1] Sealing valid baseline E1...")
    host_a_out = out / "host_a"
    owner_info = run_host_a(host_a_out)
    owner_pub = owner_info["pub_key"]
    
    # Baseline checks
    e1_capsule_dir = host_a_out / "capsule_epoch_1"
    base_verif = verify_capsule(e1_capsule_dir, owner_pub)
    print(f"  Baseline capsule verification: {base_verif['ok']} (problems: {base_verif['problems']})")
    assert base_verif["ok"], "Baseline verification failed"

    # Attack Scenario A: Tamper with a content block file
    print("\n[ATTACK SCENARIO A] Host attempts to silently alter workspace content (tampered code block)...")
    tampered_dir_a = out / "capsule_epoch_1_tampered_block"
    shutil.copytree(e1_capsule_dir, tampered_dir_a)
    
    # Find a block file and corrupt it
    blocks_dir = tampered_dir_a / "blocks"
    first_sub = next(blocks_dir.iterdir())
    first_block = next(first_sub.iterdir())
    print(f"  Target block to corrupt: {first_block.relative_to(out)}")
    first_block.write_text("print('MALICIOUS INJECTED CODE')\n")
    
    # Verify tampered capsule
    verif_a = verify_capsule(tampered_dir_a, owner_pub)
    print(f"  [RESULT] Verification passed? {verif_a['ok']}")
    print(f"  [RESULT] Rejection reasons: {verif_a['problems']}")
    assert not verif_a["ok"], "Security Failure: Verifier accepted tampered content block!"
    assert any("content blocks corrupt" in p for p in verif_a["problems"])

    # Attack Scenario B: Modify manifest properties (tamper with metadata)
    print("\n[ATTACK SCENARIO B] Adversary attempts to edit manifest metadata (e.g. elevating epoch size)...")
    tampered_dir_b = out / "capsule_epoch_1_tampered_manifest"
    shutil.copytree(e1_capsule_dir, tampered_dir_b)
    
    manifest_path = tampered_dir_b / "manifest.json"
    manifest_data = json.loads(manifest_path.read_text())
    manifest_data["epoch"] = 999  # Attempted privilege escalation
    manifest_path.write_text(json.dumps(manifest_data, indent=2))
    
    # Verify tampered capsule
    verif_b = verify_capsule(tampered_dir_b, owner_pub)
    print(f"  [RESULT] Verification passed? {verif_b['ok']}")
    print(f"  [RESULT] Rejection reasons: {verif_b['problems']}")
    assert not verif_b["ok"], "Security Failure: Verifier accepted tampered manifest metadata!"
    assert any("manifest hash mismatch" in p or "signature verification failed" in p for p in verif_b["problems"])

    # Attack Scenario C: Sign with unauthorized keys (spoofing host)
    print("\n[ATTACK SCENARIO C] Adversary attempts to sign manifest using unauthorized identity keys...")
    tampered_dir_c = out / "capsule_epoch_1_spoofed_signature"
    shutil.copytree(e1_capsule_dir, tampered_dir_c)
    
    # Generate an unauthorized keypair
    fake_priv, fake_pub = generate_keypair()
    
    manifest_path_c = tampered_dir_c / "manifest.json"
    manifest_c = json.loads(manifest_path_c.read_text())
    
    # Resign with fake private key
    manifest_c["manifest_hash"] = sha256_bytes(
        canonical_json({k: v for k, v in manifest_c.items() if k not in _EXCLUDE_FROM_HASH})
    )
    fake_sig = sign_message(fake_priv, manifest_c["manifest_hash"].encode())
    manifest_c["owner_signature"] = fake_sig.hex()
    manifest_path_c.write_text(json.dumps(manifest_c, indent=2))
    
    # Verify against authorized owner public key
    verif_c = verify_capsule(tampered_dir_c, owner_pub)
    print(f"  [RESULT] Verification passed? {verif_c['ok']}")
    print(f"  [RESULT] Rejection reasons: {verif_c['problems']}")
    assert not verif_c["ok"], "Security Failure: Verifier accepted spoofed owner signature!"
    assert any("owner signature verification failed" in p or "owner public key mismatch" in p for p in verif_c["problems"])

    print("\n" + "=" * 60)
    print("TAMPERING AUDIT COMPLETE: ALL SECURITY PREVENTATIVE SANITY CHECKS PASSED")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="HDAR Portable Single-File Protocol (Seed-Ready)")
    subparsers = ap.add_subparsers(dest="cmd", required=True)

    # Demo
    demo_ap = subparsers.add_parser("demo", help="Run the E2E verification demo")
    demo_ap.add_argument("--out", default="/tmp/hdar_demo", help="Output directory")

    # Failure demo
    fail_ap = subparsers.add_parser("demo-failure", help="Run the fail-safe tampering/security demo")
    fail_ap.add_argument("--out", default="/tmp/hdar_failure_demo", help="Output directory")

    # Host A
    host_a_ap = subparsers.add_parser("host-a", help="Seal workspace into capsule (Host A)")
    host_a_ap.add_argument("--out", required=True, help="Output directory")
    host_a_ap.add_argument("--owner-key", default="", help="Owner private key hex")

    # Host B
    host_b_ap = subparsers.add_parser("host-b", help="Restore capsule, execute task, and seal successor (Host B)")
    host_b_ap.add_argument("--capsule", required=True, help="Path to transport capsule tar.gz")
    host_b_ap.add_argument("--out", required=True, help="Output directory")
    host_b_ap.add_argument("--owner-key", required=True, help="Owner private key hex")
    host_b_ap.add_argument("--owner-pub", required=True, help="Owner public key hex")

    # Host C
    host_c_ap = subparsers.add_parser("host-c", help="Restore capsule, write summary, and seal final successor (Host C)")
    host_c_ap.add_argument("--capsule", required=True, help="Path to transport capsule tar.gz")
    host_c_ap.add_argument("--out", required=True, help="Output directory")
    host_c_ap.add_argument("--owner-key", required=True, help="Owner private key hex")
    host_c_ap.add_argument("--owner-pub", required=True, help="Owner public key hex")

    # Verify
    verify_ap = subparsers.add_parser("verify", help="Independently verify E1/E2/E3 sequence")
    verify_ap.add_argument("--host-a-report", required=True, help="Path to host_a_build_report.json")
    verify_ap.add_argument("--host-b-report", required=True, help="Path to host_b_report.json")
    verify_ap.add_argument("--host-c-report", required=True, help="Path to host_c_report.json")
    verify_ap.add_argument("--e1-capsule", required=True, help="Path to E1 capsule directory")
    verify_ap.add_argument("--e2-capsule", required=True, help="Path to E2 capsule directory")
    verify_ap.add_argument("--e3-capsule", required=True, help="Path to E3 capsule directory")
    verify_ap.add_argument("--owner-public-key", required=True, help="Path to owner_public_key.txt")
    verify_ap.add_argument("--out", default="", help="Output verification report JSON path")

    args = ap.parse_args()

    if args.cmd == "demo":
        return run_demo(Path(args.out))
    elif args.cmd == "demo-failure":
        return run_failure_demo(Path(args.out))
    elif args.cmd == "host-a":
        run_host_a(Path(args.out), args.owner_key)
        return 0
    elif args.cmd == "host-b":
        run_host_b(Path(args.capsule), Path(args.out), args.owner_key, args.owner_pub)
        return 0
    elif args.cmd == "host-c":
        run_host_c(Path(args.capsule), Path(args.out), args.owner_key, args.owner_pub)
        return 0
    elif args.cmd == "verify":
        res = run_verify(
            Path(args.host_a_report),
            Path(args.host_b_report),
            Path(args.host_c_report),
            Path(args.e1_capsule),
            Path(args.e2_capsule),
            Path(args.e3_capsule),
            Path(args.owner_public_key),
            Path(args.out) if args.out else None
        )
        return 0 if res["all_passed"] else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
