"""Lightweight report-aware Q&A for the educational medical report demo."""
from __future__ import annotations

import re
from config import settings
from utils.normal_ranges import PARAMETERS, RISK_RULES

_FAQ = {
    "what is hemoglobin": "Hemoglobin is a protein in red blood cells that carries oxygen from your lungs to the rest of your body.",
    "what is glucose": "Glucose is the sugar in your blood that your body uses as a main source of energy.",
    "what is hdl": "HDL is often called 'good' cholesterol because it helps transport excess cholesterol away from tissues.",
    "what is ldl": "LDL is often called 'bad' cholesterol because higher levels can contribute to cholesterol buildup in artery walls.",
    "what is vitamin d": "Vitamin D supports bone health, calcium absorption, and immune function.",
    "what is tsh": "TSH (thyroid-stimulating hormone) signals your thyroid gland and helps regulate thyroid hormone production.",
    "what foods improve hemoglobin": "Iron-containing foods include legumes, leafy greens, fortified foods, eggs and meat. Vitamin C can improve absorption of plant-based iron. Food choices should not replace medical evaluation of low hemoglobin.",
    "what foods lower cholesterol": "Soluble-fiber foods such as oats and beans, unsaturated fats, regular activity, and an overall balanced diet can support cholesterol management. Individual treatment decisions belong with a clinician.",
}

_SEMANTIC_MODEL = None


def _try_load_semantic_model():
    global _SEMANTIC_MODEL
    if not settings.enable_semantic_chatbot:
        return False
    if _SEMANTIC_MODEL is not None:
        return _SEMANTIC_MODEL
    try:
        from sentence_transformers import SentenceTransformer
        _SEMANTIC_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _SEMANTIC_MODEL = False
    return _SEMANTIC_MODEL


def _semantic_match(question: str, choices: list[str]) -> str | None:
    model = _try_load_semantic_model()
    if not model:
        return None
    from sentence_transformers import util
    q_emb = model.encode(question, convert_to_tensor=True)
    c_emb = model.encode(choices, convert_to_tensor=True)
    scores = util.cos_sim(q_emb, c_emb)[0]
    best_idx = int(scores.argmax())
    return choices[best_idx] if float(scores[best_idx]) >= 0.45 else None


def _keyword_match(question: str, choices: list[str]) -> str | None:
    q_words = set(re.findall(r"[a-z0-9]+", question.lower()))
    best, best_score = None, 0
    for choice in choices:
        c_words = set(re.findall(r"[a-z0-9]+", choice.lower()))
        overlap = len(q_words & c_words)
        if overlap > best_score:
            best, best_score = choice, overlap
    return best if best_score > 0 else None


def _find_parameter_in_question(question: str) -> str | None:
    q_lower = question.lower()
    for name, info in PARAMETERS.items():
        if name.lower() in q_lower:
            return name
        for alias in info["aliases"]:
            try:
                if re.search(alias, q_lower, re.IGNORECASE):
                    return name
            except re.error:
                continue
    return None


def _report_summary(report_params: list[dict]) -> str:
    flagged = [p for p in report_params if p["status"] != "Normal"]
    if not flagged:
        return (
            f"I detected {len(report_params)} supported values and all fall inside this app's demonstration intervals. "
            "Compare them with the reference intervals printed on your laboratory report."
        )
    details = ", ".join(f"{p['name']} {p['value']} {p['unit']} ({p['status']})" for p in flagged)
    return (
        f"I detected {len(report_params)} supported values. {len(flagged)} are outside this app's demonstration intervals: {details}. "
        "These are educational flags, not diagnoses; use your laboratory's own intervals and discuss unexpected results with a healthcare professional."
    )


def answer_question(question: str, report_params: list | None = None) -> str:
    question_clean = question.strip()
    q = question_clean.lower()

    if report_params:
        if any(phrase in q for phrase in ("abnormal", "flagged", "out of range", "outside range", "outside the range")):
            flagged = [p for p in report_params if p["status"] != "Normal"]
            if not flagged:
                return "None of the detected supported values are outside this app's demonstration intervals. Always compare with your laboratory's printed ranges."
            return "Flagged detected values: " + "; ".join(
                f"{p['name']} {p['value']} {p['unit']} ({p['status']})" for p in flagged
            ) + ". These are educational flags, not diagnoses."

        if any(phrase in q for phrase in ("summarize", "summary", "overall", "how is my report", "what does my report show")):
            return _report_summary(report_params)

        if any(phrase in q for phrase in ("normal values", "which are normal", "in range")):
            normal = [p for p in report_params if p["status"] == "Normal"]
            if not normal:
                return "None of the detected supported values fall inside this app's demonstration intervals."
            return "Detected values inside the demonstration intervals: " + ", ".join(
                f"{p['name']} ({p['value']} {p['unit']})" for p in normal
            ) + "."

    param_name = _find_parameter_in_question(question_clean)
    if param_name and report_params:
        match = next((p for p in report_params if p["name"] == param_name), None)
        if match and match["status"] != "Normal":
            rule = RISK_RULES.get((param_name, match["status"]))
            if rule:
                tips = "; ".join(rule["suggestions"])
                return (
                    f"Your detected {param_name} value was {match['value']} {match['unit']} ({match['status']}). "
                    f"Educational note: {rule['risk']} General information in this project includes: {tips}. "
                    "This is not a diagnosis or treatment recommendation; compare with your lab's reference interval and discuss concerns with a qualified healthcare professional."
                )
        if match:
            info = PARAMETERS[param_name]
            return (
                f"Your detected {param_name} value was {match['value']} {match['unit']}. It falls inside this app's demonstration interval "
                f"({info['low']}-{info['high']} {match['unit']}). Your laboratory's printed interval takes priority."
            )

    choices = list(_FAQ)
    matched_key = _semantic_match(question_clean, choices) or _keyword_match(question_clean, choices)
    if matched_key:
        return _FAQ[matched_key]

    if param_name:
        return f"{param_name} {PARAMETERS[param_name]['description']}."

    return (
        "I can explain detected lab parameters or summarize the selected report. Try 'Which values are abnormal?', "
        "'Summarize my report', 'What does HDL mean?', or 'Why is my glucose high?'. For medical concerns, consult a healthcare professional."
    )
