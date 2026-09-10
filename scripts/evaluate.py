"""python -m scripts.evaluate --output reports/evaluation.json"""
import argparse
import json
import tempfile
from pathlib import Path
from backend.db import Store
from backend.seed import seed
from backend.evaluation import run_evaluation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/evaluation.json")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        store = Store(str(Path(directory) / "eval.sqlite3"))
        seed(store)
        workflow = store.get("workflows", "evidence-workflow")["versions"][0]
        prompts = store.get("prompts", "evidence-summary")["versions"]
        report = run_evaluation(workflow, prompts)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    table = ["# Evaluation report", "", report["data_label"], "", f"Executed: {report['created_at']}", f"Dataset SHA-256: `{report['dataset_sha256']}`", "", "| Variant | Passed / cases | Format | Grounding | Mean latency ms | Pending human review |", "|---|---:|---:|---:|---:|---:|"]
    for row in report["comparison"]:
        table.append(f"| {row['variant']} | {row['passed']} / {row['cases']} | {row['format_validity']:.1%} | {row['evidence_grounding']:.1%} | {row['latency_ms_mean']} | {row['pending_human_review']} |")
    table.extend(["", *[f"- {line}" for line in report["limitations"]], "", "Agent: skipped — no demonstrated autonomous tool need.", "", "The extractive provider follows output_mode configuration. It does not understand or optimize prompt prose. Prompt V1 is the plain-text contract baseline; V2 is a structured exact-extract contract. Their difference is not evidence of LLM intelligence or a real user benefit."])
    path.with_suffix(".md").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "executions": len(report["results"]), "comparison": report["comparison"]}, indent=2))


if __name__ == "__main__":
    main()
