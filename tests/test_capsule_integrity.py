"""Test capsule seal, verify, and restore integrity."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hdar import (
    seal_workspace,
    verify_capsule,
    restore_workspace,
    hash_workspace,
    generate_keypair,
    sha256_bytes,
)


@pytest.fixture
def demo_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "src").mkdir()
    (ws / "data").mkdir()
    (ws / "data" / "input.jsonl").write_text('{"id":"1","category":"a","value":1.0}\n')
    (ws / "src" / "main.py").write_text("print('hello')\n")
    (ws / "todo.md").write_text("# Tasks\n- [x] done\n")
    return ws


@pytest.fixture
def owner_keys():
    return generate_keypair()


class TestSealAndVerify:
    def test_seal_creates_valid_capsule(self, demo_workspace, tmp_path, owner_keys):
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        manifest = seal_workspace(
            demo_workspace, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        assert (capsule / "manifest.json").exists()
        assert (capsule / "receipt.json").exists()
        assert (capsule / "blocks").exists()
        assert manifest["epoch"] == 1
        assert manifest["manifest_hash"] is not None

    def test_verify_passes_on_fresh_capsule(self, demo_workspace, tmp_path, owner_keys):
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        seal_workspace(
            demo_workspace, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        result = verify_capsule(capsule, pub)
        assert result["ok"], f"Problems: {result['problems']}"
        assert result["owner_signed"] is True
        assert result["signature_valid"] is True

    def test_verify_detects_corrupt_block(self, demo_workspace, tmp_path, owner_keys):
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        seal_workspace(
            demo_workspace, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        manifest = json.loads((capsule / "manifest.json").read_text())
        first_entry = manifest["workspace_manifest"]["files"][0]
        block = capsule / "blocks" / first_entry["sha256"][:2] / first_entry["sha256"]
        block.write_bytes(b"corrupted")
        result = verify_capsule(capsule, pub)
        assert not result["ok"]
        assert any("corrupt" in p for p in result["problems"])

    def test_verify_detects_missing_block(self, demo_workspace, tmp_path, owner_keys):
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        seal_workspace(
            demo_workspace, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        manifest = json.loads((capsule / "manifest.json").read_text())
        first_entry = manifest["workspace_manifest"]["files"][0]
        block = capsule / "blocks" / first_entry["sha256"][:2] / first_entry["sha256"]
        block.unlink()
        result = verify_capsule(capsule, pub)
        assert not result["ok"]
        assert any("missing" in p for p in result["problems"])

    def test_verify_detects_tampered_manifest(self, demo_workspace, tmp_path, owner_keys):
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        seal_workspace(
            demo_workspace, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        manifest = json.loads((capsule / "manifest.json").read_text())
        manifest["objective"] = "tampered"
        (capsule / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
        result = verify_capsule(capsule, pub)
        assert not result["ok"]
        assert any("manifest hash mismatch" in p for p in result["problems"])

    def test_verify_detects_wrong_owner_key(self, demo_workspace, tmp_path, owner_keys):
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        seal_workspace(
            demo_workspace, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        other_priv, other_pub = generate_keypair()
        result = verify_capsule(capsule, other_pub)
        assert not result["ok"]
        assert any("public key mismatch" in p for p in result["problems"])


class TestRestore:
    def test_restore_exact_match(self, demo_workspace, tmp_path, owner_keys):
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        seal_workspace(
            demo_workspace, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        dest = tmp_path / "restored"
        result = restore_workspace(capsule, dest)
        assert result["exact"] is True
        assert result["file_count"] > 0

    def test_restore_preserves_file_modes(self, tmp_path, owner_keys):
        ws = tmp_path / "workspace"
        ws.mkdir()
        script = ws / "run.sh"
        script.write_text("#!/bin/bash\necho hi\n")
        script.chmod(0o755)
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        seal_workspace(
            ws, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        dest = tmp_path / "restored"
        restore_workspace(capsule, dest)
        restored_script = dest / "run.sh"
        assert restored_script.exists()
        assert (restored_script.stat().st_mode & 0o777) == 0o755

    def test_restore_overwrites_existing(self, demo_workspace, tmp_path, owner_keys):
        priv, pub = owner_keys
        capsule = tmp_path / "capsule"
        seal_workspace(
            demo_workspace, capsule,
            epoch=1, parent_manifest_hash=None,
            source_host_label="test-host",
            objective="test", continuation_point="test",
            owner_private_key=priv, owner_public_key=pub,
        )
        dest = tmp_path / "restored"
        dest.mkdir()
        (dest / "junk.txt").write_text("garbage")
        restore_workspace(capsule, dest)
        assert not (dest / "junk.txt").exists()


class TestHashWorkspace:
    def test_deterministic_hash(self, demo_workspace):
        h1 = hash_workspace(demo_workspace)
        h2 = hash_workspace(demo_workspace)
        assert h1["root_hash"] == h2["root_hash"]

    def test_hash_changes_on_modification(self, demo_workspace):
        h1 = hash_workspace(demo_workspace)
        (demo_workspace / "new_file.txt").write_text("new")
        h2 = hash_workspace(demo_workspace)
        assert h1["root_hash"] != h2["root_hash"]

    def test_hash_excludes_symlinks(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "real.txt").write_text("real")
        (ws / "link.txt").symlink_to(ws / "real.txt")
        result = hash_workspace(ws)
        rel_paths = [f["rel_path"] for f in result["files"]]
        assert "real.txt" in rel_paths
        assert "link.txt" not in rel_paths
