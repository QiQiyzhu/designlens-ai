"""UTC, explicit cohort, ordered project funnel. Null means no denominator."""
import json
from datetime import datetime, timedelta, timezone


FUNNEL = ["project_created", "source_uploaded", "insight_accepted", "opportunity_created", "experiment_created"]


def ratio(numerator: int, denominator: int):
    return round(numerator / denominator, 4) if denominator else None


def analyze(store, is_demo: bool = True) -> dict:
    current = datetime.now(timezone.utc)
    since_day = (current - timedelta(days=1)).isoformat()
    since_week = (current - timedelta(days=7)).isoformat()
    with store.connect() as db:
        records = [dict(row) for row in db.execute("SELECT * FROM events WHERE is_demo=? ORDER BY timestamp,rowid", (int(is_demo),))]
        dau = db.execute("SELECT COUNT(DISTINCT user_id) FROM events WHERE is_demo=? AND timestamp>=?", (int(is_demo), since_day)).fetchone()[0]
        wau = db.execute("SELECT COUNT(DISTINCT user_id) FROM events WHERE is_demo=? AND timestamp>=?", (int(is_demo), since_week)).fetchone()[0]
        run_rows = [dict(row) for row in db.execute("SELECT * FROM workflow_runs WHERE is_demo=?", (int(is_demo),))]
    positions = {}
    milestones = {}
    for record in records:
        project = record["project_id"]
        position = positions.get(project, 0)
        if position < len(FUNNEL) and record["name"] == FUNNEL[position]:
            positions[project] = position + 1
            milestones.setdefault(project, {})[record["name"]] = record["timestamp"]
    funnel = [{"event": event, "projects": sum(position >= i + 1 for position in positions.values())} for i, event in enumerate(FUNNEL)]
    insights = [item for item in store.all("insights") if item["is_demo"] == is_demo]
    accepted = [item for item in insights if item["status"] == "accepted"]
    rejected = [item for item in insights if item["status"] == "rejected"]
    source_index = {s["id"]: s for s in store.all("sources")}
    covered = sum(bool(i["evidence_ids"]) and all(key in source_index for key in i["evidence_ids"]) for i in accepted)
    opportunities = [item for item in store.all("opportunities") if item["is_demo"] == is_demo]
    confirmed = [item for item in opportunities if item.get("human_decision", {}).get("decision") == "confirmed"]
    experiments = [item for item in store.all("experiments") if item["is_demo"] == is_demo]
    terminal = [r for r in run_rows if r["status"] in ("completed", "failed", "rejected", "abstained")]
    successful = [r for r in terminal if r["status"] in ("completed", "abstained")]
    activation_eligible = 0
    activated = 0
    for milestone in milestones.values():
        created = datetime.fromisoformat(milestone["project_created"])
        if current - created >= timedelta(days=7):
            activation_eligible += 1
            accepted_at = milestone.get("insight_accepted")
            if accepted_at and datetime.fromisoformat(accepted_at) - created <= timedelta(days=7):
                activated += 1
    adoption = []
    all_projects = len({r["project_id"] for r in records})
    for event in ["source_uploaded", "workflow_run", "evaluation_run", "experiment_created"]:
        count = len({r["project_id"] for r in records if r["name"] == event})
        adoption.append({"feature": event, "projects": count, "rate": ratio(count, all_projects)})
    latencies = sorted(r["latency_ms"] for r in terminal)
    def percentile(fraction):
        return latencies[min(len(latencies) - 1, int((len(latencies) - 1) * fraction))] if latencies else None
    # The MVP only creates experiment protocols. None satisfy the validated-decision definition.
    return {"data_label": "DEMO/SYNTHETIC activity — not real user behavior" if is_demo else "LOCAL REAL-DATA activity — not yet validated product outcomes",
            "is_demo": is_demo, "generated_at": current.isoformat(), "timezone": "UTC", "dau": dau, "wau": wau,
            "weekly_validated_decisions": 0, "validated_decisions_status": "PENDING REAL USER RESEARCH; completed study + human outcome review required",
            "funnel": funnel, "funnel_unit": "ordered distinct projects; all-time selected cohort",
            "activation": {"rate": ratio(activated, activation_eligible), "numerator": activated, "denominator": activation_eligible, "window": "7 days; only matured projects"},
            "insight_acceptance": {"rate": ratio(len(accepted), len(accepted) + len(rejected)), "accepted": len(accepted), "rejected": len(rejected)},
            "evidence_coverage": {"rate": ratio(covered, len(accepted)), "covered": covered, "accepted": len(accepted), "limitation": "Referential integrity, not semantic truth"},
            "opportunity_conversion": {"rate": ratio(len({e["opportunity_id"] for e in experiments if any(o["id"] == e["opportunity_id"] for o in confirmed)}), len(confirmed)), "confirmed_opportunities": len(confirmed), "protocols": len(experiments)},
            "workflow_success": {"rate": ratio(len(successful), len(terminal)), "successful": len(successful), "terminal": len(terminal), "pending_approval": sum(r["status"] == "pending_approval" for r in run_rows)},
            "latency_ms": {"p50": percentile(0.5), "p95": percentile(0.95), "n": len(latencies)},
            "feature_adoption": adoption, "week4_retention": None, "retention_status": "Not measured; no matured real activation cohort",
            "event_count": len(records), "recent_events": [{**r, "properties": json.loads(r["properties"])} for r in records[-15:]][::-1]}
