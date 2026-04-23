#!/usr/bin/env python3
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "stage292.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS verification_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    input_url TEXT NOT NULL,
    manifest_text TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    decision TEXT NOT NULL,
    trust_score REAL NOT NULL,
    fail_closed INTEGER NOT NULL,
    reasons_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verification_results_created_at
ON verification_results(created_at DESC);
"""

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()

    print(f"[OK] initialized SQLite DB: {DB_PATH}")

if __name__ == "__main__":
    main()
