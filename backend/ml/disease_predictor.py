"""
ml/disease_predictor.py

Rule-based "risk classification" over parsed parameters.

Labelled as ML-adjacent because this is exactly the kind of problem you'd
eventually train a classifier for (predict risk category from lab values).
Here it's implemented as a transparent, explainable rule engine — which is
actually preferable for a health-education tool, since every output can be
traced back to a specific rule instead of a opaque model decision.

A drop-in ML upgrade path is sketched in `train_ml_classifier()` at the
bottom, for discussion in interviews.
"""

from utils.normal_ranges import RISK_RULES


def analyze_risks(parsed_params: list) -> list:
    """Map abnormal parameters to educational risk notes + lifestyle tips."""
    risks = []
    for p in parsed_params:
        key = (p["name"], p["status"])
        rule = RISK_RULES.get(key)
        if rule:
            risks.append({
                "parameter": p["name"],
                "status": p["status"],
                "risk": rule["risk"],
                "suggestions": rule["suggestions"],
            })
    return risks


def compute_health_score(parsed_params: list) -> int:
    """A simple 0-100 'wellness score' = % of parameters within normal range.

    This is a coarse, illustrative metric only — not a clinical score.
    """
    if not parsed_params:
        return 0
    normal = sum(1 for p in parsed_params if p["status"] == "Normal")
    return round((normal / len(parsed_params)) * 100)


def train_ml_classifier():
    """OPTIONAL upgrade path (not wired in by default).

    If you collect a labelled dataset of (parameter vector -> risk category),
    you could replace the rule engine with a real classifier, e.g.:

        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier()
        clf.fit(X_train, y_train)   # X = parameter values, y = risk labels

    This is intentionally left unimplemented — the rule-based system above
    is safer and more explainable for an educational healthcare tool, but
    this function exists as a discussion point / extension idea.
    """
    raise NotImplementedError("Optional extension — not required for the core app.")
