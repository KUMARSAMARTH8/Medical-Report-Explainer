"""Deterministic, plain-language explanations for detected lab parameters."""
from utils.normal_ranges import PARAMETERS


def explain_parameter(param: dict) -> str:
    name = param["name"]
    status = param["status"]
    value = param["value"]
    unit = param["unit"]
    info = PARAMETERS[name]
    description = info["description"]
    ref = f"{info['low']}-{info['high']} {unit}"

    if status == "Normal":
        return (
            f"{name}: {value} {unit}. This falls inside this app's demonstration reference interval "
            f"({ref}). {name} {description}. Your own laboratory's printed interval should take priority."
        )

    direction = "below" if status.lower() in ("low", "deficient") else "above"
    return (
        f"{name}: {value} {unit}. This is {direction} this app's demonstration reference interval "
        f"({ref}) and is labelled {status}. {name} {description}. Reference intervals vary, so use the "
        f"range printed on the original report and discuss unexpected results with a healthcare professional."
    )


def summarize_report(parsed_params: list) -> dict:
    explanations = []
    flagged_count = 0
    for param in parsed_params:
        explanations.append(
            {"name": param["name"], "status": param["status"], "explanation": explain_parameter(param)}
        )
        if param["status"] != "Normal":
            flagged_count += 1

    total = len(parsed_params)
    if total == 0:
        overview = "No recognizable supported lab parameters were detected in this report."
    elif flagged_count == 0:
        overview = (
            f"All {total} detected values fall inside this app's demonstration reference intervals. "
            "Compare them with the ranges printed by your laboratory."
        )
    else:
        overview = (
            f"{flagged_count} out of {total} detected values fall outside this app's demonstration reference "
            "intervals. This is an educational flag, not a diagnosis."
        )
    return {"overview": overview, "explanations": explanations}
