"""FastAPI backend + static frontend server for the Medical Report Explainer."""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import settings
from utils.logger import get_logger
from utils.rate_limit import RateLimitMiddleware
from nlp.extractor import extract_text, OCRUnavailableError, ocr_capabilities
from nlp.medical_parser import parse_parameters
from nlp.summarizer import summarize_report
from nlp.chatbot import answer_question
from ml.disease_predictor import analyze_risks, compute_health_score
from utils.db import init_db, save_report, get_report, get_all_reports, delete_report, clear_reports

log = get_logger(__name__)
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
REPORTS_DIR = Path(settings.reports_dir)
if not REPORTS_DIR.is_absolute():
    REPORTS_DIR = BACKEND_DIR / REPORTS_DIR
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DISCLAIMER = (
    "Educational interpretation only. Reference ranges vary by laboratory, age, sex, medications, "
    "pregnancy, and clinical context. Do not use this tool for diagnosis or treatment decisions. "
    "Discuss concerning or unexpected results with a qualified healthcare professional."
)

DEMO_TEXT = """
Complete Blood Count and Metabolic / Lipid Panel
Hemoglobin: 11.1 g/dL
WBC: 7.2 x10^3/uL
RBC: 4.8 x10^6/uL
Platelets: 268 x10^3/uL
Glucose (Fasting): 118 mg/dL
HbA1c: 5.9 %
Vitamin D: 24 ng/mL
Vitamin B12: 410 pg/mL
Total Cholesterol: 218 mg/dL
HDL Cholesterol: 52 mg/dL
LDL Cholesterol: 136 mg/dL
Triglycerides: 146 mg/dL
Creatinine: 0.9 mg/dL
Uric Acid: 5.4 mg/dL
TSH: 2.2 uIU/mL
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("%s v%s starting", settings.app_name, settings.app_version)
    log.info("Reports dir: %s", REPORTS_DIR)
    log.info("OCR capabilities: %s", ocr_capabilities())
    yield
    log.info("%s shutting down", settings.app_name)


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request data.", "errors": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error. Please try again."})


class ChatRequest(BaseModel):
    question: str = Field(max_length=1000)
    report_id: int | None = None


def _analysis_payload(filename: str, raw_text: str, persist: bool = True) -> dict:
    parameters = parse_parameters(raw_text)
    if not parameters:
        raise HTTPException(
            422,
            "No supported lab parameters were detected. Try a clearer report or use the sample report "
            "to confirm the app is working.",
        )
    summary = summarize_report(parameters)
    risks = analyze_risks(parameters)
    health_score = compute_health_score(parameters)
    report_id = save_report(filename, parameters, risks, health_score) if persist else None
    return {
        "report_id": report_id,
        "filename": filename,
        "parameters": parameters,
        "summary": summary,
        "risks": risks,
        # Kept for backwards compatibility. The UI labels this as an in-range score.
        "health_score": health_score,
        "score_label": "Detected values in range",
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "frontend_served": FRONTEND_DIR.exists(),
    }


@app.get("/api/capabilities")
def capabilities():
    return {
        "ocr": ocr_capabilities(),
        "max_upload_size_mb": settings.max_upload_size_mb,
        "allowed_extensions": sorted(settings.allowed_extension_set),
        "demo_available": True,
    }


@app.post("/api/upload")
async def upload_report(file: UploadFile = File(...)):
    original_name = Path(file.filename or "report").name
    ext = Path(original_name).suffix.lower()
    if ext not in settings.allowed_extension_set:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(settings.allowed_extension_set))}")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    saved_path = REPORTS_DIR / f"{uuid.uuid4().hex}{ext}"
    total_written = 0
    try:
        with saved_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > max_bytes:
                    raise HTTPException(413, f"File too large. Maximum is {settings.max_upload_size_mb} MB.")
                out.write(chunk)
        if total_written == 0:
            raise HTTPException(400, "The uploaded file is empty.")
        try:
            raw_text = extract_text(str(saved_path))
        except OCRUnavailableError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            log.exception("Text extraction failed for %s", original_name)
            raise HTTPException(422, f"Could not read this report: {exc}") from exc
        if not raw_text.strip():
            raise HTTPException(422, "No readable text was found in this report.")
        return _analysis_payload(original_name, raw_text)
    finally:
        await file.close()
        if settings.delete_files_after_processing and saved_path.exists():
            try:
                saved_path.unlink()
            except OSError:
                log.warning("Could not remove temporary upload %s", saved_path)


@app.post("/api/demo")
def demo_report():
    """Guaranteed working demo that exercises parser, analysis, DB, dashboard, and chat."""
    return _analysis_payload("Sample Lab Report", DEMO_TEXT)


@app.post("/api/chat")
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Question cannot be empty.")
    report_params = None
    if req.report_id is not None:
        report = get_report(req.report_id)
        if not report:
            raise HTTPException(404, "The selected report no longer exists.")
        report_params = report["parameters"]
    return {"answer": answer_question(question, report_params), "disclaimer": DISCLAIMER}


@app.get("/api/report/{report_id}")
def get_report_endpoint(report_id: int):
    report = get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    report["summary"] = summarize_report(report["parameters"])
    report["disclaimer"] = DISCLAIMER
    report["score_label"] = "Detected values in range"
    return report


@app.get("/api/reports")
def list_reports(limit: int = Query(100, ge=1, le=500)):
    return get_all_reports(limit=limit)


@app.delete("/api/report/{report_id}")
def delete_report_endpoint(report_id: int):
    if not delete_report(report_id):
        raise HTTPException(404, "Report not found")
    return {"deleted": True, "report_id": report_id}


@app.delete("/api/reports")
def clear_report_history():
    return {"deleted": clear_reports()}


# Mount the static frontend last so /api/* routes always win.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
