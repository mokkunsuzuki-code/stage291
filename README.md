# Stage291: Persistent Verification Result URL (JSON Storage)

## Overview

Stage291 upgrades Stage290 by adding **JSON-based persistence** for verification results.

Users can:

- Input URL + manifest
- Get verification result (accept / pending / reject)
- Receive trust score and breakdown
- Generate a shareable verification URL
- Store results as JSON for later retrieval

This stage transforms:

Verification UI → Persistent Verification Record

---

## Key Features

### 1. Human-Friendly Verification UI
No terminal or JSON parsing required.

### 2. Persistent Result Storage
Each verification result is stored as:

results/<verification_id>.json

### 3. Shareable Verification URL

Example:

https://stage291.onrender.com/result/<verification_id>

---

### 4. Trust Model

The system evaluates:

- Integrity
- Execution
- Identity
- Time

Final decision:

- ACCEPT
- PENDING
- REJECT

---

### 5. Fail-Closed Design

If verification is incomplete:

→ system does NOT accept  
→ returns pending or reject

---

## Architecture

User (Browser)
↓
Stage291 UI
↓
Stage289 API
↓
Result + Evidence
↓
JSON storage
↓
Re-loadable verification page

---

## Flow

1. Input URL + manifest
2. POST to Stage289 API
3. Receive decision + trust score
4. Save JSON record
5. Generate shareable URL
6. Reload anytime via /result/<id>

---

## Why This Matters

Previous stages:

- Stage289 → machine verification
- Stage290 → human-friendly UI

Stage291 adds:

- persistence
- reproducibility
- shareable proof structure

This is the transition from:

verification experience → verification record

---

## Storage Model

- JSON file per verification
- Simple, transparent, inspectable
- Easy to upgrade to DB later

---

## Limitation (Important)

Render free tier:

- filesystem persistence is NOT guaranteed across redeploys

Local environment:

- persistence works reliably

---

## Next Stage

Stage292:

- SQLite persistence
- stronger durability
- production-ready verification records

---

## License

MIT License (2025)
