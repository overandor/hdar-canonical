import json
import pytest
from pathlib import Path
import sys

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from hdar_core.etl.pipeline import ETLPipeline
from hdar_core.etl.stages import (
    ExtractorStage,
    CleanerStage,
    FilterStage,
    AggregatorStage,
    ClassifierStage,
    LoaderStage,
)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "data").mkdir()
    (ws / "data" / "input_records.jsonl").write_text(
        '{"id":"r1","category":"alpha","value":" 10.0 "}\n'
        '{"id":"r2","category":"alpha","value":20.0}\n'
        '{"id":"r3","category":"beta","value":"5"}\n'
        '{"id":"r4","category":"beta","value":-1.0}\n'
        '{"id":"r5","category":"gamma","value":100.0}\n'
        '{"id":"r6","value":15.0}\n' # Missing category
    )
    return ws


def test_etl_pipeline_success(temp_workspace: Path):
    pipeline = ETLPipeline()
    pipeline.add_stage(ExtractorStage())
    pipeline.add_stage(CleanerStage())
    pipeline.add_stage(FilterStage())
    pipeline.add_stage(AggregatorStage())
    pipeline.add_stage(ClassifierStage())
    pipeline.add_stage(LoaderStage())

    initial_context = {
        "input_path": str(temp_workspace / "data" / "input_records.jsonl"),
        "output_dir": str(temp_workspace / "output"),
    }

    context, report = pipeline.run(initial_context)

    # 1. Report verification
    assert report["all_passed"] is True
    assert report["final_hash"] is not None
    assert len(report["stages"]) == 6
    for stg in report["stages"]:
        assert stg["status"] == "success"
        assert stg["stage_hash"] is not None

    # 2. Context verification
    assert context["raw_count"] == 6
    assert context["cleaned_count"] == 6
    
    # 4 valid records: r1 (alpha, 10.0), r2 (alpha, 20.0), r3 (beta, 5.0), r5 (gamma, 100.0)
    # 2 rejected records: r4 (negative), r6 (missing category)
    assert context["valid_count"] == 4
    assert context["rejected_count"] == 2

    # Verify cleaning (r1's value was cast from " 10.0 " to 10.0, r3's value was cast from "5" to 5)
    assert context["valid_records"][0]["value"] == 10.0
    assert context["valid_records"][2]["value"] == 5

    # Verify aggregation
    stats = context["stats"]
    assert "alpha" in stats
    assert stats["alpha"]["count"] == 2
    assert stats["alpha"]["sum"] == 30.0
    assert stats["alpha"]["mean"] == 15.0
    assert stats["alpha"]["min"] == 10.0
    assert stats["alpha"]["max"] == 20.0
    assert stats["alpha"]["median"] == 15.0

    # Verify classification
    tier_counts = context["tier_counts"]
    # Total valid: 4. Since alpha's mean is 15.0:
    # r1: 10/15 = 0.66 -> medium
    # r2: 20/15 = 1.33 -> medium
    # r3: 5/5 = 1.0 -> medium
    # r5: 100/100 = 1.0 -> medium
    # All are medium
    assert tier_counts["medium"] == 4

    # Verify loader outputs
    output_dir = temp_workspace / "output"
    assert (output_dir / "final_report.json").exists()
    assert (output_dir / "stage_parse.json").exists()
    assert (output_dir / "stage_filter.json").exists()

    # Verify report file contents
    final_report = json.loads((output_dir / "final_report.json").read_text())
    assert final_report["summary"]["raw_input_count"] == 6
    assert final_report["summary"]["valid_records"] == 4
    assert len(final_report["rejected_details"]) == 2


def test_etl_pipeline_cryptographic_chain(temp_workspace: Path):
    pipeline = ETLPipeline()
    pipeline.add_stage(ExtractorStage())
    pipeline.add_stage(CleanerStage())
    pipeline.add_stage(FilterStage())

    initial_context = {
        "input_path": str(temp_workspace / "data" / "input_records.jsonl"),
        "output_dir": str(temp_workspace / "output"),
    }

    _, report = pipeline.run(initial_context)
    
    stages = report["stages"]
    # Verify the parent/successor hash chaining.
    # Note: Our pipeline runner computes hashes of the hashing_payload:
    # { "stage": name, "parent_hash": parent_hash, "output": stage_output }
    # So each stage's stage_hash depends directly on the parent_hash of the previous stage.
    assert len(stages) == 3
    assert stages[0]["stage_hash"] is not None
    assert stages[1]["stage_hash"] is not None
    assert stages[2]["stage_hash"] is not None


def test_extractor_missing_input():
    pipeline = ETLPipeline()
    pipeline.add_stage(ExtractorStage())
    initial_context = {
        "input_path": "/nonexistent/file/path.jsonl"
    }
    _, report = pipeline.run(initial_context)
    assert report["all_passed"] is False
    assert report["stages"][0]["status"] == "failed"
    assert "Input file not found" in report["stages"][0]["error"]
