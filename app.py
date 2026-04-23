#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, Response

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "stage295.db"

DEFAULT_STAGE289_VERIFY_URL = "http://127.0.0.1:2890/api/verify"
STAGE289_VERIFY_URL = os.environ.get("STAGE289_VERIFY_URL", DEFAULT_STAGE289_VERIFY_URL)

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
        result_json TEXT NOT NULL,
        upstream_source TEXT NOT NULL,
        upstream_status TEXT NOT NULL
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


def normalize_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_reason_item(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return {
            "item": str(item.get("item", "unknown")),
            "ok": bool(item.get("ok", False)),
            "message": str(item.get("message", "")),
        }

    return {
        "item": "unknown",
        "ok": False,
        "message": str(item),
    }


def normalize_stage289_result(payload: dict[str, Any], manifest_text: str) -> dict[str, Any]:
    manifest_sha256 = str(payload.get("manifest_sha256", "")).strip() or sha256_text(manifest_text)

    reasons_raw = payload.get("reasons", [])
    if not isinstance(reasons_raw, list):
        reasons_raw = []

    normalized_reasons = [normalize_reason_item(item) for item in reasons_raw]

    decision = str(payload.get("decision", "reject")).strip().lower()
    if decision not in {"accept", "pending", "reject"}:
        decision = "reject"

    trust_score = max(0.0, min(1.0, round(normalize_float(payload.get("trust_score", 0.0), 0.0), 3)))
    fail_closed = normalize_bool(payload.get("fail_closed", True), True)
    verified_at = str(payload.get("verified_at", "")).strip() or utc_now_iso()

    return {
        "decision": decision,
        "trust_score": trust_score,
        "fail_closed": fail_closed,
        "reasons": normalized_reasons,
        "manifest_sha256": manifest_sha256,
        "verified_at": verified_at,
        "upstream_source": "stage289",
        "upstream_status": "ok",
    }


def call_stage289_verify(input_url: str, manifest_text: str) -> dict[str, Any]:
    payload = {
        "url": input_url,
        "manifest": manifest_text,
    }
    request_body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        STAGE289_VERIFY_URL,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            status_code = resp.getcode()
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "error_type": "http_error",
            "status_code": exc.code,
            "message": f"Stage289 returned HTTP {exc.code}",
            "body": error_body,
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "error_type": "url_error",
            "status_code": None,
            "message": f"Stage289 connection failed: {exc.reason}",
            "body": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "error_type": "unexpected_error",
            "status_code": None,
            "message": f"Stage289 call failed: {exc}",
            "body": "",
        }

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error_type": "invalid_json",
            "status_code": status_code,
            "message": "Stage289 response was not valid JSON.",
            "body": raw,
        }

    result_candidate = parsed.get("result", parsed)
    if not isinstance(result_candidate, dict):
        return {
            "ok": False,
            "error_type": "invalid_shape",
            "status_code": status_code,
            "message": "Stage289 response JSON shape was invalid.",
            "body": raw,
        }

    normalized = normalize_stage289_result(result_candidate, manifest_text)
    return {
        "ok": True,
        "status_code": status_code,
        "result": normalized,
        "raw_response": parsed,
    }


def build_fail_closed_error_result(manifest_text: str, message: str, body: str = "") -> dict[str, Any]:
    reasons = [
        {
            "item": "stage289_connection",
            "ok": False,
            "message": message,
        }
    ]

    if body.strip():
        reasons.append({
            "item": "stage289_response_body",
            "ok": False,
            "message": body[:500],
        })

    return {
        "decision": "reject",
        "trust_score": 0.0,
        "fail_closed": True,
        "reasons": reasons,
        "manifest_sha256": sha256_text(manifest_text.strip()),
        "verified_at": utc_now_iso(),
        "upstream_source": "stage289",
        "upstream_status": "error",
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
                result_json,
                upstream_source,
                upstream_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                result.get("upstream_source", "unknown"),
                result.get("upstream_status", "unknown"),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def parse_filters(args) -> tuple[str, str, float | None, int]:
    limit_raw = args.get("limit", "20")
    decision = args.get("decision", "").strip().lower()
    url_query = args.get("url_query", "").strip()
    min_score_raw = args.get("min_score", "").strip()

    try:
        limit = max(1, min(1000, int(limit_raw)))
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

    return decision, url_query, min_score, limit


def query_results(decision: str, url_query: str, min_score: float | None, limit: int) -> list[dict[str, Any]]:
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
        SELECT id, created_at, input_url, manifest_sha256, decision, trust_score, fail_closed, upstream_source, upstream_status
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
            "manifest_sha256": row["manifest_sha256"],
            "decision": row["decision"],
            "trust_score": row["trust_score"],
            "fail_closed": bool(row["fail_closed"]),
            "upstream_source": row["upstream_source"],
            "upstream_status": row["upstream_status"],
        })
    return items


@app.route("/")
def index():
    return render_template("index.html", stage289_verify_url=STAGE289_VERIFY_URL)


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "stage": 295,
        "storage": "sqlite",
        "integration": "stage289",
        "export": ["json", "csv"],
        "db_path": str(DB_PATH.name),
        "stage289_verify_url": STAGE289_VERIFY_URL,
    })


@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json(silent=True) or {}
    input_url = str(data.get("url", "")).strip()
    manifest_text = str(data.get("manifest", "")).strip()

    upstream = call_stage289_verify(input_url, manifest_text)

    if upstream["ok"]:
        result = upstream["result"]
    else:
        result = build_fail_closed_error_result(
            manifest_text=manifest_text,
            message=upstream["message"],
            body=upstream.get("body", ""),
        )

    row_id = save_result(input_url, manifest_text, result)

    return jsonify({
        "ok": True,
        "saved": True,
        "id": row_id,
        "upstream_ok": upstream["ok"],
        "upstream_error": None if upstream["ok"] else {
            "type": upstream["error_type"],
            "status_code": upstream["status_code"],
            "message": upstream["message"],
        },
        "result": result,
    })


@app.route("/api/results", methods=["GET"])
def api_results():
    decision, url_query, min_score, limit = parse_filters(request.args)
    items = query_results(decision, url_query, min_score, limit)

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
            "upstream_source": row["upstream_source"],
            "upstream_status": row["upstream_status"],
            "reasons": json.loads(row["reasons_json"]),
            "result": json.loads(row["result_json"]),
        }
    })


@app.route("/api/export/json", methods=["GET"])
def api_export_json():
    decision, url_query, min_score, limit = parse_filters(request.args)
    items = query_results(decision, url_query, min_score, limit)

    payload = {
        "exported_at": utc_now_iso(),
        "stage": 295,
        "integration": "stage289",
        "filters": {
            "decision": decision,
            "url_query": url_query,
            "min_score": min_score,
            "limit": limit,
        },
        "count": len(items),
        "items": items,
    }

    filename = "stage295_export.json"
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/api/export/csv", methods=["GET"])
def api_export_csv():
    decision, url_query, min_score, limit = parse_filters(request.args)
    items = query_results(decision, url_query, min_score, limit)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "created_at",
        "input_url",
        "manifest_sha256",
        "decision",
        "trust_score",
        "fail_closed",
        "upstream_source",
        "upstream_status",
    ])

    for item in items:
        writer.writerow([
            item["id"],
            item["created_at"],
            item["input_url"],
            item["manifest_sha256"],
            item["decision"],
            item["trust_score"],
            item["fail_closed"],
            item["upstream_source"],
            item["upstream_status"],
        ])

    filename = "stage295_export.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=2950, debug=True)
