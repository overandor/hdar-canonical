import csv
import json
from pathlib import Path
from collections import defaultdict
from hdar_core.etl.pipeline import PipelineStage


class ExtractorStage(PipelineStage):
    """ETL Stage to extract raw records from JSONL or CSV file."""
    def __init__(self, name: str = "extractor"):
        super().__init__(name)

    def execute(self, context: dict) -> dict:
        input_path_str = context.get("input_path")
        if not input_path_str:
            raise ValueError("extractor: 'input_path' is missing from context.")
        
        input_path = Path(input_path_str)
        if not input_path.exists():
            raise FileNotFoundError(f"extractor: Input file not found: {input_path}")

        records = []
        if input_path.suffix.lower() == ".csv":
            with input_path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(dict(row))
        else:
            # Default to JSONL
            content = input_path.read_text(encoding="utf-8").strip()
            for line in content.split("\n"):
                if line.strip():
                    records.append(json.loads(line))

        return {
            "raw_records": records,
            "raw_count": len(records),
        }


class CleanerStage(PipelineStage):
    """ETL Stage to clean and normalize raw records."""
    def __init__(self, name: str = "cleaner"):
        super().__init__(name)

    def execute(self, context: dict) -> dict:
        raw_records = context.get("raw_records")
        if raw_records is None:
            raise ValueError("cleaner: 'raw_records' is missing from context.")

        cleaned = []
        for rec in raw_records:
            cleaned_rec = {}
            for k, v in rec.items():
                # Clean key names (strip whitespace)
                clean_k = k.strip() if isinstance(k, str) else k
                # Clean values (strip strings, cast numeric types if possible)
                if isinstance(v, str):
                    v_str = v.strip()
                    # Try casting to numeric
                    try:
                        if "." in v_str:
                            cleaned_val = float(v_str)
                        else:
                            cleaned_val = int(v_str)
                    except ValueError:
                        cleaned_val = v_str
                else:
                    cleaned_val = v
                cleaned_rec[clean_k] = cleaned_val
            cleaned.append(cleaned_rec)

        return {
            "cleaned_records": cleaned,
            "cleaned_count": len(cleaned),
        }


class FilterStage(PipelineStage):
    """ETL Stage to validate and filter records based on requirements."""
    def __init__(self, name: str = "filter"):
        super().__init__(name)

    def execute(self, context: dict) -> dict:
        cleaned_records = context.get("cleaned_records")
        if cleaned_records is None:
            raise ValueError("filter: 'cleaned_records' is missing from context.")

        valid = []
        rejected = []

        for r in cleaned_records:
            # Check required fields
            rec_id = r.get("id")
            category = r.get("category")
            value = r.get("value")

            if rec_id is None or category is None or value is None:
                rejected.append({
                    "record": r,
                    "reason": "missing_required_fields"
                })
            elif not isinstance(value, (int, float)):
                rejected.append({
                    "record": r,
                    "reason": "invalid_value_type"
                })
            elif value < 0:
                rejected.append({
                    "record": r,
                    "reason": "negative_value"
                })
            else:
                # Value is valid, ensure category is a string representation
                r["category"] = str(category).lower().strip()
                valid.append(r)

        return {
            "valid_records": valid,
            "rejected_records": rejected,
            "valid_count": len(valid),
            "rejected_count": len(rejected),
        }


class AggregatorStage(PipelineStage):
    """ETL Stage to calculate group aggregates over categories."""
    def __init__(self, name: str = "aggregator"):
        super().__init__(name)

    def execute(self, context: dict) -> dict:
        valid_records = context.get("valid_records")
        if valid_records is None:
            raise ValueError("aggregator: 'valid_records' is missing from context.")

        by_cat = defaultdict(list)
        for r in valid_records:
            by_cat[r["category"]].append(r["value"])

        stats = {}
        for cat, vals in sorted(by_cat.items()):
            vals_sorted = sorted(vals)
            n = len(vals)
            median = (
                vals_sorted[n // 2]
                if n % 2 != 0
                else (vals_sorted[n // 2 - 1] + vals_sorted[n // 2]) / 2.0
            )
            
            stats[cat] = {
                "count": n,
                "sum": round(sum(vals), 4),
                "mean": round(sum(vals) / n, 4) if n > 0 else 0.0,
                "min": min(vals),
                "max": max(vals),
                "median": median,
            }

        return {
            "categories": sorted(list(by_cat.keys())),
            "stats": stats,
        }


class ClassifierStage(PipelineStage):
    """ETL Stage to segment records based on statistical thresholds."""
    def __init__(self, name: str = "classifier"):
        super().__init__(name)

    def execute(self, context: dict) -> dict:
        valid_records = context.get("valid_records")
        stats = context.get("stats")

        if valid_records is None or stats is None:
            raise ValueError("classifier: 'valid_records' and 'stats' must exist in context.")

        tiers = {"critical": [], "high": [], "medium": [], "low": []}
        for r in valid_records:
            cm = stats[r["category"]]["mean"]
            ratio = r["value"] / cm if cm > 0 else 0
            if ratio >= 2.0:
                tiers["critical"].append(r["id"])
            elif ratio >= 1.5:
                tiers["high"].append(r["id"])
            elif ratio >= 0.5:
                tiers["medium"].append(r["id"])
            else:
                tiers["low"].append(r["id"])

        return {
            "tier_counts": {k: len(v) for k, v in tiers.items()},
            "tier_members": tiers,
        }


class LoaderStage(PipelineStage):
    """ETL Stage to write structured outputs back to disk."""
    def __init__(self, name: str = "loader"):
        super().__init__(name)

    def execute(self, context: dict) -> dict:
        output_dir_str = context.get("output_dir")
        if not output_dir_str:
            raise ValueError("loader: 'output_dir' is missing from context.")

        output_dir = Path(output_dir_str)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build clean final report payload
        report = {
            "pipeline": "modular_etl_pipeline",
            "summary": {
                "raw_input_count": context.get("raw_count", 0),
                "cleaned_count": context.get("cleaned_count", 0),
                "valid_records": context.get("valid_count", 0),
                "rejected_records": context.get("rejected_count", 0),
                "categories": context.get("categories", []),
                "tier_distribution": context.get("tier_counts", {}),
            },
            "category_stats": context.get("stats", {}),
            "tier_members": context.get("tier_members", {}),
            "rejected_details": context.get("rejected_records", []),
        }

        # Write reports
        report_path = output_dir / "final_report.json"
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)

        # Write out raw data dumps of stages for persistence/auditing
        stage_parse_path = output_dir / "stage_parse.json"
        with stage_parse_path.open("w", encoding="utf-8") as f:
            json.dump({"raw_records": context.get("raw_records")}, f, indent=2, sort_keys=True)

        stage_filter_path = output_dir / "stage_filter.json"
        with stage_filter_path.open("w", encoding="utf-8") as f:
            json.dump({
                "valid": context.get("valid_records"),
                "rejected": context.get("rejected_records")
            }, f, indent=2, sort_keys=True)

        return {
            "final_report_path": str(report_path),
            "stage_parse_path": str(stage_parse_path),
            "stage_filter_path": str(stage_filter_path),
        }
