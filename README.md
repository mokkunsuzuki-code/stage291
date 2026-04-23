# Stage293: Verification URL UI + Search / Filter + SQLite Persistence

## Overview

Stage293 extends the verification system by adding **search and filtering capabilities** on top of SQLite persistence.

This transforms the system from simple storage into a **practical verification log system**.

---

## Key Evolution

Stage291:
- UI-based verification
- JSON output

Stage292:
- SQLite persistence
- Verification history

Stage293:
- **Search / Filter enabled**
- Queryable verification logs
- Practical audit system

---

## What This Stage Proves

- Verification logs can be queried dynamically
- Results can be filtered by decision, URL, and trust score
- Both ACCEPT and REJECT outcomes are searchable
- Verification history becomes operationally usable

---

## Architecture

User Input → Verification → SQLite Storage → Search / Filter → UI Display

---

## Features

- Verification UI (browser)
- SQLite persistence (`data/stage293.db`)
- Decision filtering (accept / pending / reject)
- URL partial match search
- Trust score filtering
- Result limit control
- Detailed result inspection

---

## Example Use Cases

- Show only ACCEPT results
- Find failed (REJECT) verifications
- Search by URL keyword
- Extract high-trust results (score ≥ 0.9)

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
- limit=1–100

### Result Detail
GET /api/results/{id}

---

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python app.py

Open:
http://127.0.0.1:2930

Storage

SQLite database:
data/stage293.db

Security Model

Fail-Closed:

Invalid input → REJECT
Missing data → REJECT
No silent success
Evolution

Stage290: UI
Stage291: JSON
Stage292: SQLite
Stage293: Search / Filter (this stage)

License

MIT License
