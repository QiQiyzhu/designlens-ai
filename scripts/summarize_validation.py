"""Summarize actual test outputs without inventing result counts or business data."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = ET.parse(root / "reports/backend-tests.xml").getroot()
suites = [backend] if backend.tag == "testsuite" else list(backend.findall("testsuite"))
browser = json.loads((root / "outputs/browser-report.json").read_text(encoding="utf-8"))


def walk(suite):
    for spec in suite.get("specs", []):
        for test in spec.get("tests", []):
            for result in test.get("results", []):
                yield {"title": spec["title"], "status": result["status"], "duration_ms": result["duration"]}
    for child in suite.get("suites", []):
        yield from walk(child)


browser_cases = [item for suite in browser["suites"] for item in walk(suite)]
digest = hashlib.sha256()
for folder in ("backend", "frontend/src", "tests", "evals"):
    for path in sorted((root / folder).rglob("*")):
        if path.is_file() and path.suffix in (".py", ".tsx", ".ts", ".css", ".json"):
            digest.update(str(path.relative_to(root)).replace("\\", "/").encode())
            digest.update(path.read_bytes())
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "implementation_sha256": digest.hexdigest(),
    "backend": {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")},
    "browser": {"stats": browser["stats"], "cases": browser_cases, "database": "Isolated synthetic SQLite, port 8002; no real research database used"},
    "evaluation": {"report": "reports/evaluation.json", "executions": len(json.loads((root / "reports/evaluation.json").read_text(encoding="utf-8"))["results"]), "data_label": "SYNTHETIC development fixtures; deterministic provider; no real model benchmark"},
    "real_research": "PENDING REAL USER RESEARCH",
    "limitations": ["Browser review/rating inputs are scripted synthetic QA actions, not a real human evaluation study.", "No hosted multi-user security, actual model quality, product impact or statistically significant experiment is claimed."],
}
(root / "reports/validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(root / "reports/browser-tests.json").write_text(json.dumps(report["browser"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
broken = []
for path in [root / "README.md", *(root / "docs").rglob("*.md")]:
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):
            continue
        target = target.split("#", 1)[0]
        if not (path.parent / target).exists():
            broken.append({"document": str(path.relative_to(root)), "target": target})
print(json.dumps({"backend": report["backend"], "browser": report["browser"]["stats"], "broken_doc_links": broken}, indent=2))
if broken:
    raise SystemExit(1)
