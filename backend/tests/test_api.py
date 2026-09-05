"""
tests/test_api.py

Integration tests against the FastAPI app using TestClient (no real server
process needed). Uses a temporary SQLite DB and reports dir so tests never
touch your real data.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

# Modules whose top-level code reads `settings` at import time — these must
# be freshly imported *after* the env vars for a given test are set, or
# they'll keep using whatever config was loaded by an earlier test/module.
_RELOAD_MODULES = ["config", "utils.db", "utils.rate_limit", "main"]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Point the app at isolated, disposable storage for this test run.
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test_reports.db"))
    monkeypatch.setenv("REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("DELETE_FILES_AFTER_PROCESSING", "true")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "0")  # disable rate limiting in tests

    for mod_name in _RELOAD_MODULES:
        sys.modules.pop(mod_name, None)

    import main as main_module

    with TestClient(main_module.app) as c:
        yield c


def _make_sample_pdf_bytes() -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hemoglobin : 10.2 g/dL\nGlucose : 160 mg/dL\n")
    return doc.tobytes()


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_upload_rejects_bad_extension(client):
    res = client.post("/api/upload", files={"file": ("test.exe", b"not a report", "application/octet-stream")})
    assert res.status_code == 400


def test_upload_and_analyze_pdf(client):
    pdf_bytes = _make_sample_pdf_bytes()
    res = client.post("/api/upload", files={"file": ("report.pdf", pdf_bytes, "application/pdf")})
    assert res.status_code == 200
    data = res.json()
    assert data["report_id"] >= 1
    assert any(p["name"] == "Hemoglobin" for p in data["parameters"])
    assert "disclaimer" in data


def test_chat_requires_nonempty_question(client):
    res = client.post("/api/chat", json={"question": "", "report_id": None})
    assert res.status_code == 400


def test_chat_general_question(client):
    res = client.post("/api/chat", json={"question": "what does HDL mean?"})
    assert res.status_code == 200
    assert "cholesterol" in res.json()["answer"].lower()


def test_reports_list_empty_initially(client):
    res = client.get("/api/reports")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_report_not_found(client):
    res = client.get("/api/report/99999")
    assert res.status_code == 404
