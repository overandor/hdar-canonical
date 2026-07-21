"""Test epoch lineage: E1 → E2 chain with signed capsules."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hdar import (
    seal_workspace,
    verify_capsule,
    restore_workspace,
    execute_task,
    generate_keypair,
)


@pytest.fixture
def owner_keys():
    return generate_keypair()


def _make_workspace(tmp_path: Path, name: str = "ws") -> Path:
    ws = tmp_path / name
    ws.mkdir()
    (ws / "data").mkdir()
    (ws / "data" / "input_records.jsonl").write_text(
        '{"id":"r1","category":"alpha","value":10.0}\n'
        '{"id":"r2","category":"beta","value":20.0}\n'
    )
    (ws / "todo.md").write_text("# Tasks\n")
    return ws


class TestEpochLineage:
    def test_e1_to_e2_lineage_chain(self, tmp_path, owner_keys):
        priv, pub = owner_keys
        ws = _make_workspace(tmp_path)

        # Seal E1
        cap_e1 = tmp_path / "cap_e1"
        m1 = seal_workspace(
            ws, cap_e1,
            epoch=1, parent_manifest_hash=None,
            source_host_label="host-a",
            objective="test", continuation_point="e1",
            owner_private_key=priv, owner_public_key=pub,
        )

        # Restore E1
        restored = tmp_path / "restored"
        result = restore_workspace(cap_e1, restored)
        assert result["exact"]

        # Execute pipeline on restored workspace
        execute_task(restored)

        # Seal E2
        cap_e2 = tmp_path / "cap_e2"
        m2 = seal_workspace(
            restored, cap_e2,
            epoch=2, parent_manifest_hash=m1["manifest_hash"],
            source_host_label="host-b",
            objective="test", continuation_point="e2",
            owner_private_key=priv, owner_public_key=pub,
        )

        # Verify lineage
        v2 = verify_capsule(cap_e2, pub)
        assert v2["ok"]
        assert v2["owner_signed"]
        assert v2["signature_valid"]
        assert v2["parent_manifest_hash"] == m1["manifest_hash"]
        assert v2["epoch"] == 2

    def test_e1_has_null_parent(self, tmp_path, owner_keys):
        priv, pub = owner_keys
        ws = _make_workspace(tmp_path)
        cap = tmp_path / "cap"
        seal_workspace(
            ws, cap,
            epoch=1, parent_manifest_hash=None,
            source_host_label="host-a",
            objective="test", continuation_point="e1",
            owner_private_key=priv, owner_public_key=pub,
        )
        v = verify_capsule(cap, pub)
        assert v["parent_manifest_hash"] is None

    def test_e2_manifest_differs_from_e1(self, tmp_path, owner_keys):
        priv, pub = owner_keys
        ws = _make_workspace(tmp_path)

        cap_e1 = tmp_path / "cap_e1"
        m1 = seal_workspace(
            ws, cap_e1,
            epoch=1, parent_manifest_hash=None,
            source_host_label="host-a",
            objective="test", continuation_point="e1",
            owner_private_key=priv, owner_public_key=pub,
        )

        restored = tmp_path / "restored"
        restore_workspace(cap_e1, restored)
        execute_task(restored)

        cap_e2 = tmp_path / "cap_e2"
        m2 = seal_workspace(
            restored, cap_e2,
            epoch=2, parent_manifest_hash=m1["manifest_hash"],
            source_host_label="host-b",
            objective="test", continuation_point="e2",
            owner_private_key=priv, owner_public_key=pub,
        )

        assert m1["manifest_hash"] != m2["manifest_hash"]

    def test_workspace_root_changes_after_pipeline(self, tmp_path, owner_keys):
        priv, pub = owner_keys
        ws = _make_workspace(tmp_path)

        cap_e1 = tmp_path / "cap_e1"
        m1 = seal_workspace(
            ws, cap_e1,
            epoch=1, parent_manifest_hash=None,
            source_host_label="host-a",
            objective="test", continuation_point="e1",
            owner_private_key=priv, owner_public_key=pub,
        )

        e1_root = m1["workspace_manifest"]["root_hash"]

        restored = tmp_path / "restored"
        restore_workspace(cap_e1, restored)
        execute_task(restored)

        cap_e2 = tmp_path / "cap_e2"
        m2 = seal_workspace(
            restored, cap_e2,
            epoch=2, parent_manifest_hash=m1["manifest_hash"],
            source_host_label="host-b",
            objective="test", continuation_point="e2",
            owner_private_key=priv, owner_public_key=pub,
        )

        e2_root = m2["workspace_manifest"]["root_hash"]
        assert e1_root != e2_root

    def test_three_epoch_chain(self, tmp_path, owner_keys):
        priv, pub = owner_keys
        ws = _make_workspace(tmp_path)

        # E1
        cap_e1 = tmp_path / "cap_e1"
        m1 = seal_workspace(
            ws, cap_e1,
            epoch=1, parent_manifest_hash=None,
            source_host_label="host-a",
            objective="test", continuation_point="e1",
            owner_private_key=priv, owner_public_key=pub,
        )

        # E2
        restored1 = tmp_path / "r1"
        restore_workspace(cap_e1, restored1)
        execute_task(restored1)
        cap_e2 = tmp_path / "cap_e2"
        m2 = seal_workspace(
            restored1, cap_e2,
            epoch=2, parent_manifest_hash=m1["manifest_hash"],
            source_host_label="host-b",
            objective="test", continuation_point="e2",
            owner_private_key=priv, owner_public_key=pub,
        )

        # E3
        restored2 = tmp_path / "r2"
        restore_workspace(cap_e2, restored2)
        execute_task(restored2)
        cap_e3 = tmp_path / "cap_e3"
        m3 = seal_workspace(
            restored2, cap_e3,
            epoch=3, parent_manifest_hash=m2["manifest_hash"],
            source_host_label="host-c",
            objective="test", continuation_point="e3",
            owner_private_key=priv, owner_public_key=pub,
        )

        # Verify full chain
        v3 = verify_capsule(cap_e3, pub)
        assert v3["ok"]
        assert v3["parent_manifest_hash"] == m2["manifest_hash"]
        v2 = verify_capsule(cap_e2, pub)
        assert v2["parent_manifest_hash"] == m1["manifest_hash"]
