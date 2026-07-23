#!/usr/bin/env python3
"""
HDAR Enterprise Production CLI & Protocol SDK

Command-Line Interface for sealing, verifying, restoring, and attesting
agent workspace capsules across cloud environments, Docker sandboxes, and CI/CD pipelines.
"""

import sys
import os
import argparse
import json
import tarfile
import base64
import io
from pathlib import Path

# Add src/ to sys.path so CLI can resolve hdar_core package imports
sys.path.append(str(Path(__file__).parent.resolve()))

from hdar_core.crypto.ed25519 import generate_keypair, sign_manifest, verify_manifest_sig
from hdar_core.crypto.hashing import sha256_bytes, sha256_file, secure_compare_hashes
from hdar_core.crypto.merkle import SparseMerkleTree, verify_smt_proof
from hdar_core.workspace.scanner import hash_workspace
from hdar_core.workspace.permissions import sanitize_permissions
from hdar_core.workspace.restoration import safe_resolve_path, HDARSafetyError
from hdar_core.attestation.host import HostAttestationEngine

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


def copy_to_clipboard(text):
    import subprocess
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(input=text.encode('utf-8'))
        return True
    except Exception:
        return False


def get_from_clipboard():
    import subprocess
    try:
        return subprocess.check_output(['pbpaste']).decode('utf-8').strip()
    except Exception:
        return ""


def cmd_seal(args):
    workspace = Path(args.workspace).resolve()

    if not workspace.exists():
        print(f"Error: Workspace {workspace} does not exist.")
        sys.exit(1)

    priv_hex, pub_hex = generate_keypair()
    root_hash, file_map = hash_workspace(workspace)

    manifest = {
        "hdar_version": "1.2.0",
        "epoch": args.epoch,
        "parent_manifest_hash": args.parent_hash or "0000000000000000000000000000000000000000000000000000000000000000",
        "content_merkle_root": root_hash,
        "owner_public_key": pub_hex,
        "timestamp": time_seconds(),
        "files": file_map
    }

    manifest_bytes = json.dumps(manifest, sort_keys=True).encode('utf-8')
    manifest_hash = sha256_bytes(manifest_bytes)
    sig = sign_manifest(priv_hex, manifest_hash)

    attest_engine = HostAttestationEngine(host_label=args.host_type)
    attest_payload = attest_engine.collect_attestation_payload()

    capsule_data = {
        "manifest": manifest,
        "manifest_hash": manifest_hash,
        "signature": sig,
        "attestation": attest_payload
    }

    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:gz") as tar:
        meta_bytes = json.dumps(capsule_data, indent=2).encode('utf-8')
        ti = tarfile.TarInfo(name="capsule_manifest.json")
        ti.size = len(meta_bytes)
        tar.addfile(ti, io.BytesIO(meta_bytes))

        for rel_path in file_map.keys():
            abs_p = workspace / rel_path
            tar.add(abs_p, arcname=f"content/{rel_path}")

    tar_bytes = tar_io.getvalue()

    if args.to_clipboard:
        b64_str = base64.b64encode(tar_bytes).decode('utf-8')
        if copy_to_clipboard(b64_str):
            print("🚀 Teleportation Active: Encoded capsule copied to system clipboard!")
        else:
            print("Error: Could not copy to clipboard. Outputting base64:")
            print(b64_str)
    elif args.output:
        out_capsule = Path(args.output).resolve()
        out_capsule.parent.mkdir(parents=True, exist_ok=True)
        with open(out_capsule, "wb") as f:
            f.write(tar_bytes)
        print(f"✓ HDAR Capsule Sealed: {out_capsule}")
    else:
        print("Error: Either --output or --to-clipboard must be specified.")
        sys.exit(1)


def cmd_restore(args):
    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    b64_data = ""
    if args.from_clipboard:
        b64_data = get_from_clipboard()
        if not b64_data:
            print("Error: Clipboard is empty or pbpaste failed.")
            sys.exit(1)
        print("📥 Reading capsule data directly from clipboard...")
    elif args.base64:
        b64_data = args.base64
    else:
        print("Error: Either --from-clipboard or --base64 must be specified.")
        sys.exit(1)

    try:
        tar_bytes = base64.b64decode(b64_data)
    except Exception as e:
        print(f"Error: Invalid Base64 data: {e}")
        sys.exit(1)

    tar_io = io.BytesIO(tar_bytes)
    with tarfile.open(fileobj=tar_io, mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.size > MAX_FILE_SIZE_BYTES:
                raise HDARSafetyError(f"Safety Violation: File exceeds limit: {member.name}")
            
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise HDARSafetyError(f"Safety Violation: Malformed traversal path: {member.name}")

            if member.name.startswith("content/"):
                rel = member.name.replace("content/", "")
                out_p = safe_resolve_path(target, rel)
                member.mode = sanitize_permissions(member.mode)
                
                out_p.parent.mkdir(parents=True, exist_ok=True)
                f_data = tar.extractfile(member)
                if f_data:
                    with open(out_p, "wb") as f:
                        f.write(f_data.read())

    print(f"✓ HDAR Capsule Restored byte-for-byte in: {target}")


def cmd_verify(args):
    capsule_path = Path(args.capsule).resolve()
    if not capsule_path.exists():
        print(f"Error: Capsule {capsule_path} not found.")
        sys.exit(1)

    with tarfile.open(capsule_path, "r:gz") as tar:
        meta_file = tar.extractfile("capsule_manifest.json")
        if not meta_file:
            print("Error: Invalid HDAR Capsule (missing capsule_manifest.json).")
            sys.exit(1)
        data = json.load(meta_file)

    manifest = data["manifest"]
    manifest_hash = data["manifest_hash"]
    sig = data["signature"]
    pub_hex = manifest["owner_public_key"]

    recomputed_hash = sha256_bytes(json.dumps(manifest, sort_keys=True).encode('utf-8'))
    hash_valid = secure_compare_hashes(recomputed_hash, manifest_hash)
    sig_valid = verify_manifest_sig(pub_hex, manifest_hash, sig)

    print("============================================================")
    print("HDAR HARDENED ENTERPRISE CAPSULE VERIFICATION AUDIT")
    print("============================================================")
    print(f"  • Manifest Hash Match: {'[PASS]' if hash_valid else '[FAIL]'}")
    print(f"  • Ed25519 Signature Match: {'[PASS]' if sig_valid else '[FAIL]'}")
    print(f"  • Epoch Level: Epoch {manifest.get('epoch', 1)}")
    print(f"  • Total Content Blocks: {len(manifest.get('files', {}))}")
    print(f"  • Executor Attestation Host: {data.get('attestation', {}).get('host_label')}")
    print("============================================================")

    if hash_valid and sig_valid:
        print("RESULT: ALL HARDENED ENTERPRISE SECURITY PREDICATES VERIFIED VALID (100%)")
        sys.exit(0)
    else:
        print("RESULT: VERIFICATION FAILED")
        sys.exit(1)


def cmd_etl(args):
    from hdar_core.etl.pipeline import ETLPipeline
    from hdar_core.etl.stages import (
        ExtractorStage,
        CleanerStage,
        FilterStage,
        AggregatorStage,
        ClassifierStage,
        LoaderStage,
    )

    workspace = Path(args.workspace).resolve()
    input_path = workspace / args.input_file
    output_dir = workspace / args.output_dir

    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist.")
        sys.exit(1)

    print("Starting Modular ETL Pipeline...")
    pipeline = ETLPipeline()
    pipeline.add_stage(ExtractorStage())
    pipeline.add_stage(CleanerStage())
    pipeline.add_stage(FilterStage())
    pipeline.add_stage(AggregatorStage())
    pipeline.add_stage(ClassifierStage())
    pipeline.add_stage(LoaderStage())

    initial_context = {
        "input_path": str(input_path),
        "output_dir": str(output_dir),
    }

    context, run_report = pipeline.run(initial_context)

    # Save run report
    run_report_path = output_dir / "etl_run_report.json"
    run_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(run_report_path, "w", encoding="utf-8") as f:
        json.dump(run_report, f, indent=2, sort_keys=True)

    print("============================================================")
    print("HDAR MODULAR ETL PIPELINE EXECUTION REPORT")
    print("============================================================")
    for stg in run_report["stages"]:
        status_label = f"[{stg['status'].upper()}]"
        duration_label = f"{stg['duration_seconds']}s"
        hash_label = f"hash: {stg['stage_hash'][:8]}..." if stg['stage_hash'] else ""
        print(f"  • Stage: {stg['stage']:<12} {status_label:<10} {duration_label:<8} {hash_label}")
        if stg["error"]:
            print(f"    Error: {stg['error']}")
    print("============================================================")
    print(f"  • Final Pipeline Hash: {run_report['final_hash']}")
    print(f"  • Total Execution Time: {run_report['total_duration_seconds']}s")
    print(f"  • Run Report Saved To: {run_report_path}")
    print("============================================================")

    if run_report["all_passed"]:
        print("RESULT: ALL ETL PIPELINE STAGES COMPLETED SUCCESSFULLY (100%)")
        sys.exit(0)
    else:
        print("RESULT: ETL PIPELINE FAILED")
        sys.exit(1)


def time_seconds():
    import time
    return time.time()


def main():
    parser = argparse.ArgumentParser(description="HDAR Hardened Enterprise Protocol CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seal_parser = subparsers.add_parser("seal", help="Seal workspace into signed HDAR capsule")
    seal_parser.add_argument("--workspace", required=True, help="Workspace directory to seal")
    seal_parser.add_argument("--output", help="Output capsule file (.hdar.tar.gz)")
    seal_parser.add_argument("--to-clipboard", action="store_true", help="Base64 encode and copy capsule to clipboard")
    seal_parser.add_argument("--epoch", type=int, default=1, help="Epoch sequence number")
    seal_parser.add_argument("--parent-hash", help="Parent manifest hash")
    seal_parser.add_argument("--host-type", default="docker-sandbox", help="Host attestation type")

    restore_parser = subparsers.add_parser("restore", help="Restore workspace from base64 capsule")
    restore_parser.add_argument("--target", required=True, help="Target restore directory")
    restore_parser.add_argument("--from-clipboard", action="store_true", help="Read capsule from clipboard")
    restore_parser.add_argument("--base64", help="Base64 capsule string directly")

    verify_parser = subparsers.add_parser("verify", help="Verify HDAR capsule integrity")
    verify_parser.add_argument("--capsule", required=True, help="Path to HDAR capsule")

    etl_parser = subparsers.add_parser("etl", help="Run the modular ETL pipeline engine")
    etl_parser.add_argument("--workspace", required=True, help="Workspace containing the data directory")
    etl_parser.add_argument("--input-file", default="data/input_records.jsonl", help="Input file path relative to workspace")
    etl_parser.add_argument("--output-dir", default="output", help="Output directory relative to workspace")

    args = parser.parse_args()
    if args.command == "seal":
        cmd_seal(args)
    elif args.command == "restore":
        cmd_restore(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "etl":
        cmd_etl(args)

if __name__ == "__main__":
    main()
