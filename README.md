# Stage295: Verification URL UI + Stage289 API Integration + Search / Filter + Export + SQLite Persistence

## Overview

Stage295 integrates the verification UI and persistence system with the real verification backend provided by **Stage289 Verification API**.

This stage replaces local dummy verification with **upstream API-based verification**, while preserving search, filtering, export, and SQLite-based persistence.

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
- JSON / CSV export
- External sharing / submission ready

Stage295:
- **Real API integration**
- Verification delegated to Stage289
- Full-stack verification workflow

---

## What This Stage Proves

- Verification can be delegated to a real upstream verification API
- Verification UI, persistence, search, and export can operate on upstream results
- Upstream verification failures are handled fail-closed
- Verification history records both result and upstream status

---

## Architecture

User Input  
→ Stage295 UI  
→ Stage289 Verification API  
→ Verification Result  
→ SQLite Storage  
→ Search / Filter  
→ Export (JSON / CSV)

---

## Features

- Verification UI (browser)
- Real Stage289 API integration
- SQLite persistence (`data/stage295.db`)
- Decision filtering (`accept / pending / reject`)
- URL partial match search
- Trust score filtering
- JSON export
- CSV export
- Upstream source / status recording
- Detailed result inspection
- Fail-closed on upstream failure

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

## Stage289 Integration

Default upstream verification endpoint:

http://127.0.0.1:2890/api/verify

Override with environment variable:

```bash
export STAGE289_VERIFY_URL="http://127.0.0.1:2890/api/verify"

Stage295 delegates verification to Stage289 instead of making a local decision.

Local Run
Start Stage289
cd ~/Desktop/test/stage289
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
Start Stage295
cd ~/Desktop/test/stage295
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py

Open:
http://127.0.0.1:2950

Storage

SQLite database:
data/stage295.db

Security Model

Fail-Closed:

Invalid input → REJECT
Missing data → REJECT
Upstream API failure → REJECT
No silent success
Why This Stage Matters

Stage294 made verification logs portable.

Stage295 makes them real.

This means the system is no longer only a UI/logging layer:
it is now connected to the actual verification backend.

Evolution

Stage290: UI
Stage291: JSON
Stage292: SQLite
Stage293: Search / Filter
Stage294: Export
Stage295: Stage289 API Integration (this stage)

License

MIT License
