import time
from pathlib import Path
from hdar_core.agent.unpacker import BaseUnpacker
from hdar_core.agent.verifier import BaseVerifier
from hdar_core.agent.generator import BaseGenerator


class MultiBackendLazyRunner:
    """Orchestrates multi-backend unpacking, validation, and deferred generation."""
    def __init__(self, unpacker: BaseUnpacker, verifiers: list[BaseVerifier], generator: BaseGenerator):
        self.unpacker = unpacker
        self.verifiers = verifiers
        self.generator = generator

    def execute_pipeline(self, capsule_path: Path, workspace_dir: Path, prompt: str) -> tuple[dict, dict]:
        start_time = time.time()
        stage_reports = []
        capsule_data = {}
        generator_output = {}
        all_passed = True

        # --- STAGE 1: Unpack ---
        stage_start = time.time()
        try:
            capsule_data = self.unpacker.unpack(capsule_path, workspace_dir)
            status = "success"
            error = None
        except Exception as e:
            status = "failed"
            error = str(e)
            all_passed = False
        
        stage_reports.append({
            "stage": "unpack",
            "status": status,
            "duration_seconds": round(time.time() - stage_start, 4),
            "error": error
        })

        # --- STAGE 2: Verification Chain ---
        if all_passed:
            for verifier in self.verifiers:
                stage_start = time.time()
                name = verifier.__class__.__name__
                try:
                    verified = verifier.verify(capsule_data, workspace_dir)
                    if verified:
                        status = "success"
                        error = None
                    else:
                        status = "failed"
                        error = "Verifier failed check."
                        all_passed = False
                except Exception as e:
                    status = "failed"
                    error = str(e)
                    all_passed = False

                stage_reports.append({
                    "stage": f"verify_{name}",
                    "status": status,
                    "duration_seconds": round(time.time() - stage_start, 4),
                    "error": error
                })
                
                if not all_passed:
                    break

        # --- STAGE 3: Generator (Invoked at the very last moment) ---
        if all_passed:
            stage_start = time.time()
            try:
                context = {
                    "capsule_data": capsule_data,
                    "workspace_dir": str(workspace_dir)
                }
                generator_output = self.generator.generate(prompt, context)
                status = generator_output.get("status", "success")
                error = generator_output.get("error")
                if status == "failed":
                    all_passed = False
            except Exception as e:
                status = "failed"
                error = str(e)
                all_passed = False

            stage_reports.append({
                "stage": "generator_execution",
                "status": status,
                "duration_seconds": round(time.time() - stage_start, 4),
                "error": error
            })
        else:
            # We explicitly skipped generation due to validation failure
            stage_reports.append({
                "stage": "generator_execution",
                "status": "skipped",
                "duration_seconds": 0.0,
                "error": "Pipeline verification failed in a previous stage."
            })

        total_duration = time.time() - start_time
        
        run_report = {
            "all_passed": all_passed,
            "total_duration_seconds": round(total_duration, 4),
            "stages": stage_reports,
        }

        # Combine results into final context
        final_context = {
            "capsule_data": capsule_data,
            "generator_output": generator_output,
            "workspace_dir": str(workspace_dir)
        }

        return final_context, run_report
