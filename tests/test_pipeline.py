"""Test the canonical 5-stage pipeline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from hdar import execute_task, sha256_bytes, canonical_json


@pytest.fixture
def pipeline_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "data").mkdir()
    (ws / "data" / "input_records.jsonl").write_text(
        '{"id":"r1","category":"alpha","value":10.0}\n'
        '{"id":"r2","category":"alpha","value":20.0}\n'
        '{"id":"r3","category":"beta","value":5.0}\n'
        '{"id":"r4","category":"beta","value":-1.0}\n'
        '{"id":"r5","category":"gamma","value":100.0}\n'
    )
    return ws


class TestPipelineStages:
    def test_all_five_stages_produce_output(self, pipeline_workspace):
        execute_task(pipeline_workspace)
        out = pipeline_workspace / "output"
        assert (out / "stage_parse.json").exists()
        assert (out / "stage_filter.json").exists()
        assert (out / "stage_aggregate.json").exists()
        assert (out / "stage_classify.json").exists()
        assert (out / "final_report.json").exists()

    def test_parse_stage_loads_all_records(self, pipeline_workspace):
        execute_task(pipeline_workspace)
        parse = json.loads((pipeline_workspace / "output" / "stage_parse.json").read_text())
        assert parse["records_loaded"] == 5
        assert parse["first_id"] == "r1"
        assert parse["last_id"] == "r5"

    def test_filter_rejects_negative_values(self, pipeline_workspace):
        execute_task(pipeline_workspace)
        filt = json.loads((pipeline_workspace / "output" / "stage_filter.json").read_text())
        assert filt["valid_count"] == 4
        assert filt["rejected_count"] == 1
        assert filt["rejected"][0]["id"] == "r4"
        assert filt["rejected"][0]["reason"] == "invalid_value"

    def test_aggregate_computes_stats(self, pipeline_workspace):
        execute_task(pipeline_workspace)
        agg = json.loads((pipeline_workspace / "output" / "stage_aggregate.json").read_text())
        assert "alpha" in agg["stats"]
        assert agg["stats"]["alpha"]["count"] == 2
        assert agg["stats"]["alpha"]["sum"] == 30.0
        assert agg["stats"]["alpha"]["mean"] == 15.0

    def test_classify_assigns_tiers(self, pipeline_workspace):
        execute_task(pipeline_workspace)
        cls = json.loads((pipeline_workspace / "output" / "stage_classify.json").read_text())
        total = sum(cls["tier_counts"].values())
        assert total == 4  # 4 valid records

    def test_final_report_summarizes(self, pipeline_workspace):
        execute_task(pipeline_workspace)
        report = json.loads((pipeline_workspace / "output" / "final_report.json").read_text())
        assert report["summary"]["total_input"] == 5
        assert report["summary"]["valid_records"] == 4
        assert report["summary"]["rejected"] == 1
        assert report["metadata"]["stages_completed"] == 5


class TestPipelineDeterminism:
    def test_same_input_same_output(self, pipeline_workspace, tmp_path):
        ws2 = tmp_path / "workspace2"
        ws2.mkdir()
        (ws2 / "data").mkdir()
        (ws2 / "data" / "input_records.jsonl").write_text(
            '{"id":"r1","category":"alpha","value":10.0}\n'
            '{"id":"r2","category":"alpha","value":20.0}\n'
            '{"id":"r3","category":"beta","value":5.0}\n'
            '{"id":"r4","category":"beta","value":-1.0}\n'
            '{"id":"r5","category":"gamma","value":100.0}\n'
        )
        r1 = execute_task(pipeline_workspace)
        r2 = execute_task(ws2)
        assert r1["stage_hash"] == r2["stage_hash"]

    def test_stage_hash_chain(self, pipeline_workspace):
        execute_task(pipeline_workspace)
        parse = json.loads((pipeline_workspace / "output" / "stage_parse.json").read_text())
        filt = json.loads((pipeline_workspace / "output" / "stage_filter.json").read_text())
        agg = json.loads((pipeline_workspace / "output" / "stage_aggregate.json").read_text())
        cls = json.loads((pipeline_workspace / "output" / "stage_classify.json").read_text())
        report = json.loads((pipeline_workspace / "output" / "final_report.json").read_text())
        assert filt["parent_hash"] == parse["stage_hash"]
        assert agg["parent_hash"] == filt["stage_hash"]
        assert cls["parent_hash"] == agg["stage_hash"]
        assert report["parent_hash"] == cls["stage_hash"]


class TestPipelineEdgeCases:
    def test_empty_input(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "data").mkdir()
        (ws / "data" / "input_records.jsonl").write_text("")
        with pytest.raises(IndexError):
            execute_task(ws)

    def test_all_rejected(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "data").mkdir()
        (ws / "data" / "input_records.jsonl").write_text(
            '{"id":"r1","category":"a","value":-1.0}\n'
            '{"id":"r2","category":"b","value":-2.0}\n'
        )
        execute_task(ws)
        filt = json.loads((ws / "output" / "stage_filter.json").read_text())
        assert filt["valid_count"] == 0
        assert filt["rejected_count"] == 2

    def test_missing_fields_rejected(self, tmp_path):
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "data").mkdir()
        (ws / "data" / "input_records.jsonl").write_text(
            '{"id":"r1","value":1.0}\n'
            '{"id":"r2","category":"a"}\n'
        )
        execute_task(ws)
        filt = json.loads((ws / "output" / "stage_filter.json").read_text())
        assert filt["valid_count"] == 0
        assert filt["rejected_count"] == 2
        reasons = {r["reason"] for r in filt["rejected"]}
        assert "missing_fields" in reasons
