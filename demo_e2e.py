#!/usr/bin/env python3
"""End-to-end HDAR demo: Host A seals → Host B restores, executes, seals successor.

This script runs the complete signed capsule flow in one command:
  1. Host A: create workspace, seal Epoch 1 with Ed25519 owner signature
  2. Host B: restore E1, verify signature, execute pipeline, seal Epoch 2

Usage:
    python3 demo_e2e.py --out /tmp/hdar_demo
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="HDAR end-to-end signed capsule demo")
    ap.add_argument("--out", default="/tmp/hdar_demo", help="Output directory")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    src_dir = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_dir))
    from hdar import generate_keypair

    # Generate owner keypair once — passed to both Host A and Host B
    priv, pub = generate_keypair()
    priv_hex = priv.hex()
    pub_hex = pub.hex()

    # --- Host A ---
    print("=" * 60)
    print("HOST A: Sealing Epoch 1")
    print("=" * 60)
    host_a_out = out / "host_a"
    host_a_out.mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, str(src_dir / "seal_on_host_a.py"), "--out", str(host_a_out), "--owner-key", priv_hex],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Host A FAILED:\n{result.stderr}")
        return 1

    # Verify the public key matches
    saved_pub = (host_a_out / "owner_public_key.txt").read_text().strip()
    assert saved_pub == pub_hex, f"Public key mismatch: {saved_pub} != {pub_hex}"

    transport_e1 = host_a_out / "transport_capsule_epoch_1.tar.gz"
    assert transport_e1.exists(), "Transport capsule not created"

    # --- Host B ---
    print("=" * 60)
    print("HOST B: Restoring E1, executing pipeline, sealing E2")
    print("=" * 60)
    host_b_out = out / "host_b"
    result = subprocess.run(
        [
            sys.executable, str(src_dir / "seal_on_host_b.py"),
            "--capsule", str(transport_e1),
            "--out", str(host_b_out),
            "--owner-key", priv_hex,
            "--owner-pub", pub_hex,
        ],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Host B FAILED:\n{result.stderr}")
        return 1

    # --- Step 3: Independent Verifier ---
    print("=" * 60)
    print("VERIFIER C: Independent verification")
    print("=" * 60)
    verifier_report_path = out / "verifier_report.json"
    result = subprocess.run(
        [
            sys.executable, str(src_dir / "verifier.py"),
            "--host-a-report", str(host_a_out / "host_a_build_report.json"),
            "--host-b-report", str(host_b_out / "host_b_report.json"),
            "--e1-capsule", str(host_a_out / "capsule_epoch_1"),
            "--e2-capsule", str(host_b_out / "capsule_epoch_2"),
            "--owner-public-key", str(host_a_out / "owner_public_key.txt"),
            "--out", str(verifier_report_path),
        ],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Verifier FAILED:\n{result.stderr}")
        return 1

    verifier_report = json.loads(verifier_report_path.read_text())
    print()
    print(f"  Total: {verifier_report['passed']}/{verifier_report['total_checks']} passed")
    print(f"  All hard checks passed: {verifier_report['all_passed']}")
    if verifier_report["warnings"]:
        print(f"  Warnings: {len(verifier_report['warnings'])} (expected in local demo — same platform)")
    print()
    if verifier_report["all_passed"]:
        print("ALL CHECKS PASSED — signed capsule flow verified end-to-end.")
        print(f"  E1 manifest: {verifier_report['checks'][0]['detail'][:32]}...")
        print(f"  Verifier report: {verifier_report_path}")
        return 0
    else:
        print("SOME CHECKS FAILED — review output above.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
