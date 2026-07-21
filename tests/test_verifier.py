"""Test the independent verifier against a full E1→E2 signed capsule flow."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hdar import generate_keypair


@pytest.fixture
def e2e_artifacts(tmp_path: Path) -> dict:
    """Run the full end-to-end demo and return paths to all artifacts."""
    src_dir = Path(__file__).parent.parent / "src"
    priv, pub = generate_keypair()
    priv_hex = priv.hex()
    pub_hex = pub.hex()

    # Host A
    host_a_out = tmp_path / "host_a"
    host_a_out.mkdir()
    result = subprocess.run(
        [sys.executable, str(src_dir / "seal_on_host_a.py"),
         "--out", str(host_a_out), "--owner-key", priv_hex],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"Host A failed:\n{result.stderr}"

    # Host B
    host_b_out = tmp_path / "host_b"
    transport_e1 = host_a_out / "transport_capsule_epoch_1.tar.gz"
    result = subprocess.run(
        [sys.executable, str(src_dir / "seal_on_host_b.py"),
         "--capsule", str(transport_e1),
         "--out", str(host_b_out),
         "--owner-key", priv_hex,
         "--owner-pub", pub_hex],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"Host B failed:\n{result.stderr}"

    return {
        "host_a_report": host_a_out / "host_a_build_report.json",
        "host_b_report": host_b_out / "host_b_report.json",
        "e1_capsule": host_a_out / "capsule_epoch_1",
        "e2_capsule": host_b_out / "capsule_epoch_2",
        "owner_pub_key": host_a_out / "owner_public_key.txt",
        "tmp_path": tmp_path,
    }


class TestIndependentVerifier:
    def test_verifier_passes_on_valid_flow(self, e2e_artifacts):
        v = e2e_artifacts
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "src" / "verifier.py"),
             "--host-a-report", str(v["host_a_report"]),
             "--host-b-report", str(v["host_b_report"]),
             "--e1-capsule", str(v["e1_capsule"]),
             "--e2-capsule", str(v["e2_capsule"]),
             "--owner-public-key", str(v["owner_pub_key"])],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Verifier failed:\n{result.stdout}\n{result.stderr}"
        assert "All hard checks passed: True" in result.stdout

    def test_verifier_writes_report_file(self, e2e_artifacts, tmp_path):
        v = e2e_artifacts
        out_report = tmp_path / "verifier_report.json"
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "src" / "verifier.py"),
             "--host-a-report", str(v["host_a_report"]),
             "--host-b-report", str(v["host_b_report"]),
             "--e1-capsule", str(v["e1_capsule"]),
             "--e2-capsule", str(v["e2_capsule"]),
             "--owner-public-key", str(v["owner_pub_key"]),
             "--out", str(out_report)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert out_report.exists()
        report = json.loads(out_report.read_text())
        assert report["all_passed"] is True
        assert report["total_checks"] >= 18

    def test_verifier_detects_tampered_e2_manifest(self, e2e_artifacts):
        v = e2e_artifacts
        # Tamper with E2 manifest
        e2_manifest_path = v["e2_capsule"] / "manifest.json"
        manifest = json.loads(e2_manifest_path.read_text())
        manifest["objective"] = "tampered objective"
        e2_manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "src" / "verifier.py"),
             "--host-a-report", str(v["host_a_report"]),
             "--host-b-report", str(v["host_b_report"]),
             "--e1-capsule", str(v["e1_capsule"]),
             "--e2-capsule", str(v["e2_capsule"]),
             "--owner-public-key", str(v["owner_pub_key"])],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "E2 manifest hash valid" in result.stdout
        assert "FAIL" in result.stdout

    def test_verifier_checks_signature_validity(self, e2e_artifacts):
        v = e2e_artifacts
        # Run verifier and check it reports signature checks
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "src" / "verifier.py"),
             "--host-a-report", str(v["host_a_report"]),
             "--host-b-report", str(v["host_b_report"]),
             "--e1-capsule", str(v["e1_capsule"]),
             "--e2-capsule", str(v["e2_capsule"]),
             "--owner-public-key", str(v["owner_pub_key"])],
            capture_output=True, text=True,
        )
        assert "E1 Ed25519 owner signature valid" in result.stdout
        assert "E2 Ed25519 owner signature valid" in result.stdout
        assert "[PASS]" in result.stdout

    def test_verifier_checks_lineage_chain(self, e2e_artifacts):
        v = e2e_artifacts
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "src" / "verifier.py"),
             "--host-a-report", str(v["host_a_report"]),
             "--host-b-report", str(v["host_b_report"]),
             "--e1-capsule", str(v["e1_capsule"]),
             "--e2-capsule", str(v["e2_capsule"]),
             "--owner-public-key", str(v["owner_pub_key"])],
            capture_output=True, text=True,
        )
        assert "Cryptographic lineage E1→E2" in result.stdout
        assert "Epoch advancement 1→2" in result.stdout
