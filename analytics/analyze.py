"""python -m analytics.analyze --db data/designlens.sqlite3 --demo --output reports/analytics-demo.json"""
import argparse
import json
from pathlib import Path
from backend.analytics import analyze
from backend.db import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/designlens.sqlite3")
    parser.add_argument("--demo", action="store_true", help="Explicitly select synthetic/demo activity")
    parser.add_argument("--output", default="reports/analytics.json")
    args = parser.parse_args()
    if not Path(args.db).is_file():
        raise SystemExit("Database does not exist. Start the API or use the fixture script first.")
    report = analyze(Store(args.db), args.demo)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(path), "label": report["data_label"], "event_count": report["event_count"]}))


if __name__ == "__main__":
    main()
