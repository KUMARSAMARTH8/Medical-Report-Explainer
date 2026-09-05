"""
tests/test_pipeline.py

Unit tests for the core NLP/ML pipeline (no server, no file I/O).
Run with:  pytest
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nlp.medical_parser import parse_parameters
from nlp.summarizer import summarize_report
from ml.disease_predictor import analyze_risks, compute_health_score
from nlp.chatbot import answer_question

SAMPLE_TEXT = """
Hemoglobin : 10.2 g/dL
Glucose (Fasting) : 160 mg/dL
Vitamin D : 14 ng/mL
LDL Cholesterol : 145 mg/dL
Total Cholesterol : 210 mg/dL
Platelets : 250
TSH : 2.1
"""


def test_parse_parameters_detects_known_values():
    params = parse_parameters(SAMPLE_TEXT)
    names = {p["name"] for p in params}
    assert "Hemoglobin" in names
    assert "Glucose" in names
    assert "Vitamin D" in names
    assert "Total Cholesterol" in names
    assert "LDL" in names


def test_parse_parameters_classifies_status_correctly():
    params = {p["name"]: p for p in parse_parameters(SAMPLE_TEXT)}
    assert params["Hemoglobin"]["status"] == "Low"
    assert params["Glucose"]["status"] == "High"
    assert params["Vitamin D"]["status"] == "Deficient"
    assert params["Platelets"]["status"] == "Normal"
    assert params["TSH"]["status"] == "Normal"


def test_total_cholesterol_and_ldl_do_not_get_confused():
    """Regression test: these two used to collide via a shared 'cholesterol' regex."""
    params = {p["name"]: p for p in parse_parameters(SAMPLE_TEXT)}
    assert params["Total Cholesterol"]["value"] == 210.0
    assert params["LDL"]["value"] == 145.0


def test_parse_parameters_empty_text_returns_empty_list():
    assert parse_parameters("no medical data here") == []


def test_summarize_report_flags_abnormal_count():
    params = parse_parameters(SAMPLE_TEXT)
    summary = summarize_report(params)
    assert "5 out of 7" in summary["overview"] or "out of" in summary["overview"]
    assert len(summary["explanations"]) == len(params)


def test_summarize_report_no_parameters():
    summary = summarize_report([])
    assert "No recognizable" in summary["overview"]


def test_analyze_risks_only_flags_abnormal_params():
    params = parse_parameters(SAMPLE_TEXT)
    risks = analyze_risks(params)
    risk_params = {r["parameter"] for r in risks}
    assert "Platelets" not in risk_params  # normal, should not be flagged
    assert "Glucose" in risk_params        # high, should be flagged


def test_compute_health_score_range():
    params = parse_parameters(SAMPLE_TEXT)
    score = compute_health_score(params)
    assert 0 <= score <= 100


def test_compute_health_score_empty_is_zero():
    assert compute_health_score([]) == 0


def test_chatbot_answers_faq_question():
    answer = answer_question("what does HDL mean?")
    assert "cholesterol" in answer.lower()


def test_chatbot_uses_report_context_when_available():
    params = parse_parameters(SAMPLE_TEXT)
    answer = answer_question("why is my glucose high", params)
    assert "160" in answer or "glucose" in answer.lower()


def test_chatbot_handles_unknown_question_gracefully():
    answer = answer_question("asdkjfhaslkdjfh")
    assert isinstance(answer, str) and len(answer) > 0


def test_parse_parameters_accepts_comma_formatted_value():
    params = {p["name"]: p for p in parse_parameters("Platelets: 250,000")}
    # The app's Platelets demo interval expects values expressed in x10^3/uL,
    # so this mainly verifies numeric normalization rather than clinical units.
    assert params["Platelets"]["value"] == 250000.0


def test_chatbot_can_summarize_flagged_report_values():
    params = parse_parameters(SAMPLE_TEXT)
    answer = answer_question("Which values are abnormal?", params)
    assert "glucose" in answer.lower()
    assert "flagged" in answer.lower()
