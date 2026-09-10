"""Isolated synthetic database for browser QA; never touches a research database."""
import os
import sys
from pathlib import Path
from uuid import uuid4

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.chdir(root)
os.environ["DESIGNLENS_DB"] = str(root / "data" / f"browser-{uuid4().hex}.sqlite3")
os.environ["DESIGNLENS_PROVIDER"] = "extractive"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8002, log_level="warning")
