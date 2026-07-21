"""Canonical Host B restorer.

Restores the Epoch 1 capsule from Host A, executes the canonical
pipeline task, seals the Epoch 2 successor capsule with Ed25519
owner signature, and emits a Host B report.

This is the ONLY script that restores and advances epochs.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import tarfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hdar import (
    AGENT_ID,
    PROTOCOL_VERSION,
    execute_task,
    restore_workspace,
    seal_workspace,
    sha256_file,
    verify_capsule,
    safe_extract_tar,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="HDAR Host B — restore capsule, execute pipeline, seal successor"
    )
    ap.add_argument("--capsule", required=True, help="Path to transport capsule tar.gz from Host A")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--owner-key", required=True, help="Owner private key hex (must match Host A)")
    ap.add_argument("--owner-pub", required=True, help="Owner public key hex (must match Host A)")
    args = ap.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    owner_priv = bytes.fromhex(args.owner_key)
    owner_pub = bytes.fromhex(args.owner_pub)

    # --- Step 1: Extract and verify Epoch 1 capsule ---
    capsule_tar = Path(args.capsule).resolve()
    if not capsule_tar.exists():
        raise SystemExit(f"Transport capsule not found: {capsule_tar}")

    extract_dir = out_dir / "extracted_e1"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(capsule_tar, "r:gz") as tf:
        safe_extract_tar(tf, extract_dir)

    capsule_e1_dir = extract_dir / "capsule_epoch_1"
    if not capsule_e1_dir.exists():
        raise SystemExit(f"Expected capsule_epoch_1/ inside archive, not found in {extract_dir}")

    verification_e1 = verify_capsule(capsule_e1_dir, owner_pub)
    print(f"E1 verified: ok={verification_e1['ok']} sig_valid={verification_e1['signature_valid']}")
    if not verification_e1["ok"]:
        raise SystemExit(f"E1 verification failed: {verification_e1['problems']}")
    if not verification_e1["signature_valid"]:
        raise SystemExit("E1 owner signature invalid — refusing to restore unauthenticated capsule")

    e1_manifest = json.loads((capsule_e1_dir / "manifest.json").read_text())
    e1_manifest_hash = e1_manifest["manifest_hash"]
    print(f"E1 manifest_hash: {e1_manifest_hash[:16]}...")

    # --- Step 2: Restore workspace ---
    workspace = out_dir / "host_b_workspace"
    restoration = restore_workspace(capsule_e1_dir, workspace)
    print(f"Workspace restored: exact={restoration['exact']} files={restoration['file_count']}")
    if not restoration["exact"]:
        raise SystemExit(f"Restoration hash mismatch: expected {restoration['expected_root_hash'][:16]}, got {restoration['restored_root_hash'][:16]}")

    # --- Step 3: Execute canonical pipeline ---
    report = execute_task(workspace)
    print(f"Pipeline executed: stages=5 valid={report['summary']['valid_records']} rejected={report['summary']['rejected']}")

    # Update agent state
    agent_state_path = workspace / "agent_state.json"
    agent_state = json.loads(agent_state_path.read_text())
    agent_state["epoch"] = 2
    agent_state["status"] = "task_completed_on_host_b"
    agent_state["task_completed"] = True
    agent_state["host_b_label"] = "host-b-local"
    agent_state["host_b_platform"] = platform.platform()
    agent_state_path.write_text(json.dumps(agent_state, indent=2, sort_keys=True) + "\n")

    # Update progress log
    with (workspace / "progress.log").open("a") as f:
        f.write(json.dumps({
            "event": "pipeline_executed_on_host_b",
            "host": "host-b",
            "timestamp": time.time(),
            "epoch": 2,
            "stages_completed": 5,
        }, sort_keys=True) + "\n")

    # Update todo
    (workspace / "todo.md").write_text(
        "# HDAR Task List\n\n"
        "## Epoch 1 (Host A)\n"
        "- [x] Create workspace\n"
        "- [x] Seal capsule\n\n"
        "## Epoch 2 (Host B)\n"
        "- [x] Execute pipeline\n"
        "- [x] Seal successor\n"
    )

    # --- Step 4: Seal Epoch 2 successor ---
    capsule_e2_dir = out_dir / "capsule_epoch_2"
    manifest_e2 = seal_workspace(
        workspace,
        capsule_e2_dir,
        epoch=2,
        parent_manifest_hash=e1_manifest_hash,
        source_host_label="host-b-local",
        objective="Continue unfinished work after Host A runtime destruction.",
        continuation_point="Host B restored E1, executed pipeline, sealed E2 successor.",
        owner_private_key=owner_priv,
        owner_public_key=owner_pub,
    )
    print(f"E2 sealed: manifest_hash={manifest_e2['manifest_hash'][:16]}...")

    # Verify E2
    verification_e2 = verify_capsule(capsule_e2_dir, owner_pub)
    print(f"E2 verified: ok={verification_e2['ok']} sig_valid={verification_e2['signature_valid']}")
    if not verification_e2["ok"]:
        raise SystemExit(f"E2 verification failed: {verification_e2['problems']}")

    # Pack E2 transport capsule
    transport_e2 = out_dir / "transport_capsule_epoch_2.tar.gz"
    with tarfile.open(transport_e2, "w:gz") as tf:
        tf.add(capsule_e2_dir, arcname="capsule_epoch_2")
    transport_e2_hash = sha256_file(transport_e2)
    print(f"E2 transport capsule: {transport_e2.name} ({transport_e2.stat().st_size}B)")

    # --- Step 5: Write Host B report ---
    host_b_report = {
        "schema": "hdar.host-b-report/v1.0",
        "protocol_version": PROTOCOL_VERSION,
        "host_b_platform": platform.platform(),
        "e1_verification": verification_e1,
        "e1_manifest_hash": e1_manifest_hash,
        "restoration": restoration,
        "pipeline_report": {
            "summary": report["summary"],
            "stage_hash_chain": {
                "parse": report["parent_hash"],
                "final": report["stage_hash"],
            },
        },
        "e2_verification": verification_e2,
        "e2_manifest_hash": manifest_e2["manifest_hash"],
        "e2_transport": {
            "path": str(transport_e2),
            "bytes": transport_e2.stat().st_size,
            "sha256": transport_e2_hash,
        },
        "lineage": {
            "parent_manifest_hash": e1_manifest_hash,
            "child_manifest_hash": manifest_e2["manifest_hash"],
            "epoch_advanced": 1,
            "lineage_intact": verification_e2["parent_manifest_hash"] == e1_manifest_hash,
        },
        "owner_public_key": owner_pub.hex(),
        "signature_status": {
            "e1_signed": verification_e1["owner_signed"],
            "e1_signature_valid": verification_e1["signature_valid"],
            "e2_signed": verification_e2["owner_signed"],
            "e2_signature_valid": verification_e2["signature_valid"],
        },
    }
    (out_dir / "host_b_report.json").write_text(
        json.dumps(host_b_report, indent=2, sort_keys=True)
    )
    print(f"Host B report written: {out_dir / 'host_b_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
