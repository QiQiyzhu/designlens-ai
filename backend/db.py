"""SQLite persistence; one local workspace, never advertised as tenant isolation."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("DESIGNLENS_DB", "data/designlens.sqlite3")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT, is_demo INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT, created_at TEXT, is_demo INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS entities_kind ON entities(kind);
                CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, project_id TEXT NOT NULL,
                    name TEXT NOT NULL, entity_id TEXT, timestamp TEXT NOT NULL, is_demo INTEGER NOT NULL, properties TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS events_cohort ON events(is_demo,timestamp,name,project_id);
                CREATE TABLE IF NOT EXISTS workflow_runs(id TEXT PRIMARY KEY, workflow_id TEXT, user_id TEXT, project_id TEXT,
                    status TEXT, created_at TEXT, latency_ms REAL, is_demo INTEGER NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY, opportunity_id TEXT, status TEXT,
                    created_at TEXT, is_demo INTEGER NOT NULL, data TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def all(self, kind: str) -> list[dict]:
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data FROM entities WHERE kind=? ORDER BY rowid", (kind,))]

    def get(self, kind: str, entity_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT data FROM entities WHERE id=? AND kind=?", (entity_id, kind)).fetchone()
            return json.loads(row[0]) if row else None

    def put(self, kind: str, data: dict) -> dict:
        with self.connect() as db:
            db.execute("INSERT INTO entities VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (data["id"], kind, json.dumps(data, ensure_ascii=False)))
        return data

    def event(self, name: str, entity_id: str, is_demo: bool = True, properties: dict | None = None):
        with self.connect() as db:
            db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?)", (uid("evt"), "local-owner", "arc-study", name, entity_id, now(), int(is_demo), json.dumps(properties or {}, ensure_ascii=False)))

    def save_run(self, run: dict):
        with self.connect() as db:
            db.execute("INSERT INTO workflow_runs VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,latency_ms=excluded.latency_ms,data=excluded.data", (run["id"], run["workflow_id"], "local-owner", "arc-study", run["status"], run["created_at"], run["latency_ms"], int(run["is_demo"]), json.dumps(run, ensure_ascii=False)))

    def get_run(self, run_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT data FROM workflow_runs WHERE id=?", (run_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def runs(self) -> list[dict]:
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT data FROM workflow_runs ORDER BY created_at DESC LIMIT 100")]

    def save_experiment(self, item: dict):
        with self.connect() as db:
            db.execute("INSERT INTO experiments VALUES(?,?,?,?,?,?)", (item["id"], item["opportunity_id"], item["status"], item["created_at"], int(item["is_demo"]), json.dumps(item, ensure_ascii=False)))
        return self.put("experiments", item)
