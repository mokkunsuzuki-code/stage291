#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "stage293.db"

app = Flask(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    schema = """
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

    CREATE INDEX IF NOT EXISTS idx_verification_results_decision
    ON verification_results(decision);

    CREATE INDEX IF NOT EXISTS idx_verification_results_input_url
    ON verification_results(input_url);

    CREATE INDEX IF NOT EXISTS idx_verification_results_trust_score
    ON verification_results(trust_score);
    """
    conn = get_db()
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return default


def extract_fail_closed(manifest: dict[str, Any]) -> bool:
    if "fail_closed" in manifest:
        return normalize_bool(manifest["fail_closed"], True)

    policy = manifest.get("verification_policy")
    if isinstance(policy, dict) and "fail_closed" in policy:
        return normalize_bool(policy["fail_closed"], True)

    return True


def verify_payload(input_url: str, manifest_text: str) -> dict[str, Any]:
    reasons: list[dict[str, Any]] = []
    trust_score = 1.0
    decision = "accept"
    manifest: dict[str, Any] | None = None

    input_url = input_url.strip()
    manifest_text = manifest_text.strip()
    manifest_digest = sha256_text(manifest_text)

    if not input_url:
        reasons.append({
            "item": "input_url",
            "ok": False,
            "message": "URL is empty."
        })
        trust_score -= 0.40
    else:
        url_ok = input_url.startswith("http://") or input_url.startswith("https://")
        reasons.append({
            "item": "input_url",
            "ok": url_ok,
            "message": "URL must start with http:// or https://." if not url_ok else "URL format is acceptable."
        })
        if not url_ok:
            trust_score -= 0.25

    if not manifest_text:
        reasons.append({
            "item": "manifest_text",
            "ok": False,
            "message": "Manifest JSON is empty."
        })
        trust_score -= 0.60
        manifest = {}
    else:
        try:
            parsed = json.loads(manifest_text)
            if not isinstance(parsed, dict):
                raise ValueError("Manifest root must be a JSON object.")
            manifest = parsed
            reasons.append({
                "item": "manifest_json",
                "ok": True,
                "message": "Manifest JSON parsed successfully."
            })
        except Exception as exc:
            manifest = {}
            reasons.append({
                "item": "manifest_json",
                "ok": False,
                "message": f"Manifest JSON parse failed: {exc}"
            })
            trust_score -= 0.60

    fail_closed = extract_fail_closed(manifest or {})

    manifest_url = None
    for key in ("url", "target_url", "verification_url"):
        value = (manifest or {}).get(key)
        if isinstance(value, str) and value.strip():
            manifest_url = value.strip()
            break

    if manifest_url:
        url_match = manifest_url == input_url
        reasons.append({
            "item": "manifest_url_match",
            "ok": url_match,
            "message": "Manifest URL matches input URL." if url_match else f"Manifest URL does not match input URL. manifest={manifest_url}"
        })
        if not url_match:
            trust_score -= 0.20
    else:
        reasons.append({
            "item": "manifest_url_match",
            "ok": False,
            "message": "Manifest does not contain url / target_url / verification_url."
        })
        trust_score -= 0.10

    has_subject = isinstance((manifest or {}).get("subject"), dict) or isinstance((manifest or {}).get("subject"), str)
    reasons.append({
        "item": "subject",
        "ok": has_subject,
        "message": "subject exists." if has_subject else "subject is missing."
    })
    if not has_subject:
        trust_score -= 0.10

    evidence = (manifest or {}).get("evidence")
    has_evidence = isinstance(evidence, list) and len(evidence) > 0
    reasons.append({
        "item": "evidence",
        "ok": has_evidence,
        "message": "evidence exists." if has_evidence else "evidence is missing or empty."
    })
    if not has_evidence:
        trust_score -= 0.10

    trust_score = max(0.0, min(1.0, round(trust_score, 3)))

    any_hard_fail = any(not item["ok"] for item in reasons if item["item"] in {"manifest_json", "input_url"})
    any_soft_fail = any(not item["ok"] for item in reasons)

    if fail_closed and any_hard_fail:
        decision = "reject"
    elif trust_score >= 0.95 and not any_soft_fail:
        decision = "accept"
    elif trust_score >= 0.60:
        decision = "pending"
    else:
        decision = "reject"

    return {
        "decision": decision,
        "trust_score": trust_score,
        "fail_closed": fail_closed,
        "reasons": reasons,
        "manifest_sha256": manifest_digest,
        "verified_at": utc_now_iso(),
    }


def save_result(input_url: str, manifest_text: str, result: dict[str, Any]) -> int:
    conn = get_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO verification_results (
                created_at,
                input_url,
                manifest_text,
                manifest_sha256,
                decision,
                trust_score,
                fail_closed,
                reasons_json,
                result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["verified_at"],
                input_url,
                manifest_text,
                result["manifest_sha256"],
                result["decision"],
                float(result["trust_score"]),
                1 if result["fail_closed"] else 0,
                json.dumps(result["reasons"], ensure_ascii=False, indent=2),
                json.dumps(result, ensure_ascii=False, indent=2),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "stage": 293,
        "storage": "sqlite",
        "db_path": str(DB_PATH.name),
    })


@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json(silent=True) or {}
    input_url = str(data.get("url", "")).strip()
    manifest_text = str(data.get("manifest", "")).strip()

    result = verify_payload(input_url, manifest_text)
    row_id = save_result(input_url, manifest_text, result)

    return jsonify({
        "ok": True,
        "saved": True,
        "id": row_id,
        "result": result,
    })


@app.route("/api/results", methods=["GET"])
def api_results():
    limit_raw = request.args.get("limit", "20")
    decision = request.args.get("decision", "").strip().lower()
    url_query = request.args.get("url_query", "").strip()
    min_score_raw = request.args.get("min_score", "").strip()

    try:
        limit = max(1, min(100, int(limit_raw)))
    except ValueError:
        limit = 20

    allowed_decisions = {"accept", "pending", "reject"}
    if decision not in allowed_decisions:
        decision = ""

    min_score = None
    if min_score_raw:
        try:
            parsed = float(min_score_raw)
            min_score = max(0.0, min(1.0, parsed))
        except ValueError:
            min_score = None

    where_clauses = []
    params: list[Any] = []

    if decision:
        where_clauses.append("decision = ?")
        params.append(decision)

    if url_query:
        where_clauses.append("input_url LIKE ?")
        params.append(f"%{url_query}%")

    if min_score is not None:
        where_clauses.append("trust_score >= ?")
        params.append(min_score)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    query = f"""
        SELECT id, created_at, input_url, decision, trust_score, fail_closed, manifest_sha256
        FROM verification_results
        {where_sql}
        ORDER BY id DESC
        LIMIT ?
    """
    params.append(limit)

    conn = get_db()
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    items = []
    for row in rows:
        items.append({
            "id": row["id"],
            "created_at": row["created_at"],
            "input_url": row["input_url"],
            "decision": row["decision"],
            "trust_score": row["trust_score"],
            "fail_closed": bool(row["fail_closed"]),
            "manifest_sha256": row["manifest_sha256"],
        })

    return jsonify({
        "ok": True,
        "filters": {
            "decision": decision,
            "url_query": url_query,
            "min_score": min_score,
            "limit": limit,
        },
        "count": len(items),
        "items": items,
    })


@app.route("/api/results/<int:result_id>", methods=["GET"])
def api_result_detail(result_id: int):
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM verification_results
            WHERE id = ?
            """,
            (result_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"ok": False, "error": "not_found"}), 404

    return jsonify({
        "ok": True,
        "item": {
            "id": row["id"],
            "created_at": row["created_at"],
            "input_url": row["input_url"],
            "manifest_text": row["manifest_text"],
            "manifest_sha256": row["manifest_sha256"],
            "decision": row["decision"],
            "trust_score": row["trust_score"],
            "fail_closed": bool(row["fail_closed"]),
            "reasons": json.loads(row["reasons_json"]),
            "result": json.loads(row["result_json"]),
        }
    })


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=2930, debug=True)
