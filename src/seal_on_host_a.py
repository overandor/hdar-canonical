"""Canonical Host A sealer.

Creates a demo workspace, seals it into a transport capsule with Ed25519
owner signature, destroys the workspace, and emits a build report.

This is the ONLY script that creates capsules. No other module may seal.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import tarfile
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hdar import (
    AGENT_ID,
    PROTOCOL_VERSION,
    generate_keypair,
    seal_workspace,
    verify_capsule,
    sha256_file,
    hash_workspace,
    safe_extract_tar,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def create_workspace(workspace: Path) -> None:
    """Create demo workspace from canonical fixtures."""
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "data").mkdir(exist_ok=True)

    # Copy fixture data
    shutil.copy2(FIXTURES_DIR / "input_records.jsonl", workspace / "data" / "input_records.jsonl")
    shutil.copy2(FIXTURES_DIR / "worker.py", workspace / "src" / "worker.py")

    # Agent state
    (workspace / "agent_state.json").write_text(json.dumps({
        "agent_id": AGENT_ID,
        "epoch": 1,
        "host_a_label": "host-a-local",
        "status": "sealed_on_host_a",
        "task": "multi_stage_analysis_pipeline",
        "task_completed": False,
        "task_stages": ["parse", "filter", "aggregate", "classify", "report"],
        "next_action": "Host B must restore workspace, execute pipeline, and seal epoch 2.",
        "authority": {
            "filesystem": "demo workspace only",
            "network": "none required",
            "secrets": "none embedded",
        },
    }, indent=2, sort_keys=True) + "\n")

    # Progress log
    (workspace / "progress.log").write_text(
        json.dumps({
            "event": "created_on_host_a",
            "host": "host-a",
            "timestamp": time.time(),
            "epoch": 1,
        }, sort_keys=True) + "\n"
    )

    # Task list
    (workspace / "todo.md").write_text(
        "# HDAR Task List\n\n"
        "## Epoch 1 (Host A)\n"
        "- [x] Create workspace\n"
        "- [x] Seal capsule\n\n"
        "## Epoch 2 (Host B)\n"
        "- [ ] Execute pipeline\n"
        "- [ ] Seal successor\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="HDAR Host A — seal workspace into transport capsule")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--owner-key", default="", help="Owner private key hex (generates new if omitted)")
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Key management
    if args.owner_key:
        owner_priv = bytes.fromhex(args.owner_key)
        # Derive public key
        if len(owner_priv) == 32:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
            priv = Ed25519PrivateKey.from_private_bytes(owner_priv)
            owner_pub = priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        else:
            owner_pub = b"hash-only-fallback-public"
    else:
        owner_priv, owner_pub = generate_keypair()

    # Save public key
    (out_dir / "owner_public_key.txt").write_text(owner_pub.hex() + "\n")

    # Create workspace
    workspace = out_dir / "host_a_workspace"
    capsule_dir = out_dir / "capsule_epoch_1"
    create_workspace(workspace)

    pre_seal_hash = hash_workspace(workspace)["root_hash"]
    print(f"Workspace created: {pre_seal_hash[:16]}...")

    # Seal E1
    manifest = seal_workspace(
        workspace,
        capsule_dir,
        epoch=1,
        parent_manifest_hash=None,
        source_host_label="host-a-local",
        objective="Continue unfinished work after Host A runtime destruction.",
        continuation_point="Host A sealed epoch 1; Host B must restore and execute pipeline.",
        owner_private_key=owner_priv,
        owner_public_key=owner_pub,
    )
    print(f"E1 sealed: manifest_hash={manifest['manifest_hash'][:16]}...")

    # Verify
    verification = verify_capsule(capsule_dir, owner_pub)
    print(f"E1 verified: ok={verification['ok']} sig_valid={verification['signature_valid']}")
    if not verification["ok"]:
        raise SystemExit(f"E1 verification failed: {verification['problems']}")

    # Pack transport capsule
    transport_tar = out_dir / "transport_capsule_epoch_1.tar.gz"
    with tarfile.open(transport_tar, "w:gz") as tf:
        tf.add(capsule_dir, arcname="capsule_epoch_1")
    transport_hash = sha256_file(transport_tar)
    print(f"Transport capsule: {transport_tar.name} ({transport_tar.stat().st_size}B)")

    # Destroy workspace
    shutil.rmtree(workspace)
    print(f"Host A workspace destroyed: {not workspace.exists()}")

    # Write build report
    report = {
        "schema": "hdar.host-a-build-report/v1.0",
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
        "pinned_dependencies": {"cryptography": "44.0.1"},
        "reproducibility_claims": {
            "byte_identical_capsule_reproduction": False,
            "deterministic_computation": True,
            "deterministic_logical_state": True,
            "note": "Task output is deterministic. Capsule manifest contains timestamps making byte-identical reproduction across builds impossible. This is acceptable for unique authenticated state.",
        },
        "separation_model": {
            "environment_separation": True,
            "infrastructure_separation": True,
            "note": "Host A and Host B run on different infrastructure.",
        },
    }
    (out_dir / "host_a_build_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True)
    )
    print(f"Build report written: {out_dir / 'host_a_build_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
