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

    # --- Verify results ---
    print("=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    host_b_report = json.loads((host_b_out / "host_b_report.json").read_text())

    checks = [
        ("E1 signature valid", host_b_report["signature_status"]["e1_signature_valid"]),
        ("E2 signature valid", host_b_report["signature_status"]["e2_signature_valid"]),
        ("E1 → E2 lineage intact", host_b_report["lineage"]["lineage_intact"]),
        ("Restoration exact", host_b_report["restoration"]["exact"]),
        ("Pipeline stages completed", host_b_report["pipeline_report"]["summary"]["valid_records"] > 0),
    ]

    all_pass = True
    for label, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("ALL CHECKS PASSED — signed capsule flow verified end-to-end.")
        print(f"  E1 manifest: {host_b_report['e1_manifest_hash'][:32]}...")
        print(f"  E2 manifest: {host_b_report['e2_manifest_hash'][:32]}...")
        print(f"  E2 transport: {host_b_out / 'transport_capsule_epoch_2.tar.gz'}")
        return 0
    else:
        print("SOME CHECKS FAILED — review output above.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
