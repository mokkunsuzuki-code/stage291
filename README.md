# Stage294: Verification URL UI + Search / Filter + Export + SQLite Persistence

## Overview

Stage294 extends the verification log system by adding **export capabilities** on top of search, filtering, and SQLite persistence.

This stage transforms the system from an internal verification log into an **externally shareable evidence system**.

---

## Key Evolution

Stage291:
- UI-based verification
- JSON output

Stage292:
- SQLite persistence
- Verification history

Stage293:
- Search / filter
- Practical verification log system

Stage294:
- **JSON / CSV export**
- Search-aware export
- External sharing / submission ready

---

## What This Stage Proves

- Verification logs can be queried and exported
- Export output reflects search / filter conditions
- ACCEPT / REJECT results can be shared externally
- Verification evidence becomes submission-ready

---

## Architecture

User Input → Verification → SQLite Storage → Search / Filter → Export (JSON / CSV) → External Sharing

---

## Features

- Verification UI (browser)
- SQLite persistence (`data/stage294.db`)
- Decision filtering (`accept / pending / reject`)
- URL partial match search
- Trust score filtering
- Result limit control
- JSON export
- CSV export
- Detailed result inspection

---

## Example Use Cases

- Export only ACCEPT results
- Export failed REJECT verifications
- Export search results for a specific URL
- Export high-trust results only
- Submit verification evidence to external reviewers

---

## API

### Health
GET /api/health

### Verify
POST /api/verify

### Search Results
GET /api/results

Query parameters:
- decision=accept|pending|reject
- url_query=keyword
- min_score=0.0–1.0
- limit=1–1000

### Result Detail
GET /api/results/{id}

### JSON Export
GET /api/export/json

### CSV Export
GET /api/export/csv

Export endpoints support the same query parameters as `/api/results`.

---

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python app.py

Open:
http://127.0.0.1:2940

Storage

SQLite database:
data/stage294.db

Security Model

Fail-Closed:

Invalid input → REJECT
Missing data → REJECT
No silent success
Why This Stage Matters

Stage293 made verification logs searchable.

Stage294 makes them portable.

This means the system can now support:

audit submission
external review
team sharing
evidence attachment
reproducible reporting
Evolution

Stage290: UI
Stage291: JSON
Stage292: SQLite
Stage293: Search / Filter
Stage294: Export (this stage)

License

MIT License
