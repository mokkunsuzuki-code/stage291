# Stage292: Verification URL UI + SQLite Persistence

## Overview

Stage292 extends the Verification URL UI by adding **persistent storage using SQLite**.

This stage transforms verification from a one-time UI interaction into a **persistent verification log system**.

---

## Key Concept

Stage291:
- Verification via browser UI
- JSON-based output (ephemeral)

Stage292:
- Verification via browser UI
- **SQLite-based persistence**
- Verification history tracking
- Reproducible inspection

---

## What This Stage Proves

- Verification results can be stored persistently
- Each verification is reproducible and queryable
- Fail-closed decisions are recorded with reasons
- Both success and failure are auditable

---

## Architecture


User Input (URL + Manifest)
↓
Verification Logic (fail-closed)
↓
Decision + Trust Score
↓
SQLite Storage (stage292.db)
↓
History / Detail View (UI)


---

## Features

- Verification UI (browser-based)
- SQLite persistence (`data/stage292.db`)
- History listing (latest first)
- Detailed verification inspection
- Fail-closed enforcement
- Trust score calculation

---

## Example Outcomes

### ACCEPT (valid input)
- trust_score: 1.000
- decision: accept

### REJECT (invalid / empty input)
- trust_score: 0.000
- decision: reject

---

## API Endpoints

### Health Check

GET /api/health


### Verify and Save

POST /api/verify


### List Results

GET /api/results


### Result Detail

GET /api/results/{id}


---

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

python tools/init_db.py
python app.py

Open:

http://127.0.0.1:2920
Storage

SQLite file:

data/stage292.db
Important Design Principle

This system is fail-closed:

Invalid input → REJECT
Missing data → REJECT
No silent acceptance
Evolution Path

Stage290: UI (visualization layer)
Stage291: JSON persistence
Stage292: SQLite persistence (this stage)
Stage293+: Query / filtering / analytics

License

MIT License
