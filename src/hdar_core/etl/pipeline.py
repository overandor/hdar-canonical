import json
import time
import hashlib
from hdar_core.crypto.hashing import sha256_bytes


def canonical_json(data: dict) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()


class PipelineStage:
    """Base class for all ETL pipeline stages."""
    def __init__(self, name: str):
        self.name = name

    def execute(self, context: dict) -> dict:
        """Executes the pipeline stage.
        
        Args:
            context: The working context dictionary containing pipeline state.
            
        Returns:
            A dictionary containing the stage's output keys, which will be merged 
            into the pipeline context.
        """
        raise NotImplementedError("Subclasses must implement execute")


class ETLPipeline:
    """Modular and cryptographic ETL pipeline engine."""
    def __init__(self):
        self.stages: list[PipelineStage] = []
        self.history: list[dict] = []

    def add_stage(self, stage: PipelineStage) -> "ETLPipeline":
        self.stages.append(stage)
        return self

    def run(self, initial_context: dict) -> tuple[dict, dict]:
        """Runs the pipeline stages sequentially.
        
        At each stage, computes a state hash and links it cryptographically to the parent.
        
        Args:
            initial_context: The starting context (e.g. input_path, configuration)
            
        Returns:
            A tuple of (final_context, run_report).
        """
        context = dict(initial_context)
        parent_hash = "0" * 64
        self.history = []
        
        start_time = time.time()
        stage_reports = []

        for stage in self.stages:
            stage_start = time.time()
            try:
                # Run the stage logic
                stage_output = stage.execute(context)
                
                # Merge stage output into working context
                context.update(stage_output)
                
                # Build canonical payload for hashing
                # Ensure the payload includes stage metadata and the output data
                hashing_payload = {
                    "stage": stage.name,
                    "parent_hash": parent_hash,
                    "output": stage_output,
                }
                
                stage_hash = sha256_bytes(canonical_json(hashing_payload))
                
                # Update parent hash for the next stage
                parent_hash = stage_hash
                
                status = "success"
                error_msg = None
            except Exception as e:
                status = "failed"
                error_msg = str(e)
                stage_hash = None
                
            duration = time.time() - stage_start
            
            report = {
                "stage": stage.name,
                "status": status,
                "duration_seconds": round(duration, 4),
                "stage_hash": stage_hash,
                "error": error_msg,
            }
            stage_reports.append(report)
            
            if status == "failed":
                # Terminate pipeline run early on stage failure
                break

        total_duration = time.time() - start_time
        all_passed = all(r["status"] == "success" for r in stage_reports)
        
        run_report = {
            "all_passed": all_passed,
            "total_duration_seconds": round(total_duration, 4),
            "final_hash": parent_hash if all_passed else None,
            "stages": stage_reports,
        }
        
        return context, run_report
