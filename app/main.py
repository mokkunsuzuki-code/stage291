from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

STAGE289_API = "https://stage289.onrender.com/verify"
RESULTS_DIR = Path("results")

app = FastAPI(
    title="Stage291 Persistent Verification URL UI",
    description="Verification URL UI with JSON persistence on top of Stage289 Verification API.",
    version="291.0.0",
)

templates = Jinja2Templates(directory="templates")


def ensure_results_dir() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_share_url(request: Request, verification_id: str) -> str:
    return str(request.url_for("result_by_id", verification_id=verification_id))


def result_path_for(verification_id: str) -> Path:
    return RESULTS_DIR / f"{verification_id}.json"


def save_result_record(verification_id: str, record: dict[str, Any]) -> None:
    ensure_results_dir()
    path = result_path_for(verification_id)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_result_record(verification_id: str) -> dict[str, Any] | None:
    path = result_path_for(verification_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def render_result_page(
    request: Request,
    verification_id: str | None,
    verified_at: str | None,
    share_url: str | None,
    url: str | None,
    manifest_text: str | None,
    parsed_manifest: dict[str, Any] | None,
    parse_error: str | None,
    api_result: dict[str, Any] | None,
    api_error: str | None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "verification_id": verification_id,
            "verified_at": verified_at,
            "share_url": share_url,
            "url": url,
            "manifest_text": manifest_text,
            "parsed_manifest": parsed_manifest,
            "parse_error": parse_error,
            "api_result": api_result,
            "api_error": api_error,
            "api_result_pretty": pretty_json(api_result) if api_result is not None else None,
        },
        status_code=status_code,
    )


@app.on_event("startup")
def startup_event() -> None:
    ensure_results_dir()


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    sample_manifest = {
        "execution": True,
        "identity": True,
        "timestamp": True,
        "workflow": "github-actions",
        "signer": "demo-signer",
    }
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "stage": "291",
            "sample_url": "https://example.com",
            "sample_manifest": pretty_json(sample_manifest),
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "stage": "291",
        "name": "Persistent Verification URL UI",
        "status": "ok",
    }


@app.get("/result/{verification_id}", response_class=HTMLResponse, name="result_by_id")
def result_by_id(request: Request, verification_id: str) -> HTMLResponse:
    stored = load_result_record(verification_id)

    if stored is None:
        return render_result_page(
            request=request,
            verification_id=verification_id,
            verified_at=None,
            share_url=None,
            url=None,
            manifest_text=None,
            parsed_manifest=None,
            parse_error=None,
            api_result=None,
            api_error=f"Verification result '{verification_id}' was not found.",
            status_code=404,
        )

    return render_result_page(
        request=request,
        verification_id=verification_id,
        verified_at=stored.get("verified_at"),
        share_url=build_share_url(request, verification_id),
        url=stored.get("url"),
        manifest_text=stored.get("manifest_text"),
        parsed_manifest=stored.get("parsed_manifest"),
        parse_error=stored.get("parse_error"),
        api_result=stored.get("api_result"),
        api_error=stored.get("api_error"),
        status_code=200,
    )


@app.post("/verify-ui", response_class=HTMLResponse)
def verify_ui(
    request: Request,
    url: str = Form(...),
    manifest_text: str = Form(...),
) -> HTMLResponse:
    parsed_manifest: dict[str, Any] | None = None
    parse_error: str | None = None
    api_result: dict[str, Any] | None = None
    api_error: str | None = None

    verification_id = secrets.token_urlsafe(8)
    verified_at = now_iso_utc()

    try:
        loaded = json.loads(manifest_text)
        if not isinstance(loaded, dict):
            raise ValueError("manifest must be a JSON object")
        parsed_manifest = loaded
    except Exception as exc:
        parse_error = f"{type(exc).__name__}: {exc}"

    if parse_error is None:
        payload = {
            "url": url,
            "manifest": parsed_manifest,
        }
        try:
            response = requests.post(STAGE289_API, json=payload, timeout=30)
            response.raise_for_status()
            api_result = response.json()
        except Exception as exc:
            api_error = f"{type(exc).__name__}: {exc}"

    record = {
        "verification_id": verification_id,
        "verified_at": verified_at,
        "url": url,
        "manifest_text": manifest_text,
        "parsed_manifest": parsed_manifest,
        "parse_error": parse_error,
        "api_result": api_result,
        "api_error": api_error,
    }
    save_result_record(verification_id, record)

    return render_result_page(
        request=request,
        verification_id=verification_id,
        verified_at=verified_at,
        share_url=build_share_url(request, verification_id),
        url=url,
        manifest_text=manifest_text,
        parsed_manifest=parsed_manifest,
        parse_error=parse_error,
        api_result=api_result,
        api_error=api_error,
        status_code=200,
    )
