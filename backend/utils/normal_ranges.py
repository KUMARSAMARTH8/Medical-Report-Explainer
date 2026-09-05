"""
utils/normal_ranges.py

Central knowledge base of medical parameters this app understands.
Each entry defines:
  - aliases: text variants that might appear in a real report (used for regex matching)
  - unit: expected unit (for display only, not enforced)
  - low / high: normal reference range
  - low_label / high_label: how to describe an out-of-range value (e.g. "Low", "Deficient")
  - description: one-line plain-English description of what the parameter measures

NOTE: These ranges are generic adult reference ranges for demonstration purposes only.
Real lab reports vary by age, sex, lab, and method. This is an educational project,
NOT a diagnostic tool.
"""

PARAMETERS = {
    "Hemoglobin": {
        "aliases": [r"hemoglobin", r"h[ae]moglobin", r"\bhb\b"],
        "unit": "g/dL",
        "low": 12.0,
        "high": 16.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "carries oxygen from your lungs to the rest of your body",
    },
    "Glucose": {
        "aliases": [r"glucose\s*\(?fasting\)?", r"fasting\s*glucose", r"\bglucose\b", r"\bfbs\b"],
        "unit": "mg/dL",
        "low": 70.0,
        "high": 99.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "measures the sugar level in your blood",
    },
    "HbA1c": {
        "aliases": [r"hba1c", r"glycated\s*h[ae]moglobin", r"\ba1c\b"],
        "unit": "%",
        "low": 4.0,
        "high": 5.6,
        "low_label": "Low",
        "high_label": "High",
        "description": "reflects your average blood sugar over the past 2-3 months",
    },
    "Vitamin D": {
        "aliases": [r"vitamin\s*d\s*\(?25[- ]?oh\)?", r"vitamin\s*d3?", r"\bvit\.?\s*d\b"],
        "unit": "ng/mL",
        "low": 30.0,
        "high": 100.0,
        "low_label": "Deficient",
        "high_label": "High",
        "description": "supports bone health and immune function",
    },
    "Vitamin B12": {
        "aliases": [r"vitamin\s*b\s*[-]?\s*12", r"\bb12\b", r"cobalamin"],
        "unit": "pg/mL",
        "low": 200.0,
        "high": 900.0,
        "low_label": "Deficient",
        "high_label": "High",
        "description": "helps keep nerve and blood cells healthy",
    },
    "Total Cholesterol": {
        "aliases": [r"total\s*cholesterol", r"cholesterol\s*total", r"cholesterol\s*\(total\)"],
        "unit": "mg/dL",
        "low": 0.0,
        "high": 200.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "measures the total amount of cholesterol in your blood",
    },
    "HDL": {
        "aliases": [r"hdl\s*cholesterol", r"\bhdl\b"],
        "unit": "mg/dL",
        "low": 40.0,
        "high": 200.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "the 'good' cholesterol that helps clear excess cholesterol from your blood",
    },
    "LDL": {
        "aliases": [r"ldl\s*cholesterol", r"\bldl\b"],
        "unit": "mg/dL",
        "low": 0.0,
        "high": 100.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "the 'bad' cholesterol that can build up in artery walls",
    },
    "Triglycerides": {
        "aliases": [r"triglycerides"],
        "unit": "mg/dL",
        "low": 0.0,
        "high": 150.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "a type of fat in your blood used for energy",
    },
    "Creatinine": {
        "aliases": [r"creatinine"],
        "unit": "mg/dL",
        "low": 0.6,
        "high": 1.3,
        "low_label": "Low",
        "high_label": "High",
        "description": "a waste product filtered by your kidneys, used to check kidney function",
    },
    "Uric Acid": {
        "aliases": [r"uric\s*acid"],
        "unit": "mg/dL",
        "low": 3.5,
        "high": 7.2,
        "low_label": "Low",
        "high_label": "High",
        "description": "a waste product that can build up and form crystals in joints",
    },
    "Platelets": {
        "aliases": [r"platelet\s*count", r"platelets", r"\bplt\b"],
        "unit": "x10^3/uL",
        "low": 150.0,
        "high": 450.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "cell fragments that help your blood clot",
    },
    "WBC": {
        "aliases": [r"wbc\s*count", r"white\s*blood\s*cell", r"\bwbc\b"],
        "unit": "x10^3/uL",
        "low": 4.0,
        "high": 11.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "white blood cells that help fight infection",
    },
    "RBC": {
        "aliases": [r"rbc\s*count", r"red\s*blood\s*cell", r"\brbc\b"],
        "unit": "x10^6/uL",
        "low": 4.2,
        "high": 5.9,
        "low_label": "Low",
        "high_label": "High",
        "description": "red blood cells that carry oxygen throughout your body",
    },
    "TSH": {
        "aliases": [r"tsh", r"thyroid\s*stimulating\s*hormone"],
        "unit": "uIU/mL",
        "low": 0.4,
        "high": 4.0,
        "low_label": "Low",
        "high_label": "High",
        "description": "signals your thyroid gland to regulate metabolism",
    },
}

# Rule-based risk + lifestyle knowledge base.
# Keyed as (parameter_name, status_label) -> {risk, suggestions}
RISK_RULES = {
    ("Hemoglobin", "Low"): {
        "risk": "Possible anemia, which can cause fatigue, weakness, or dizziness.",
        "suggestions": [
            "Include iron-rich foods like leafy greens, legumes, and lean meats",
            "Pair iron-rich meals with vitamin C to improve absorption",
            "Discuss iron studies with a doctor if fatigue persists",
        ],
    },
    ("Glucose", "High"): {
        "risk": "Possible risk of pre-diabetes or diabetes.",
        "suggestions": [
            "Reduce intake of refined sugar and sugary drinks",
            "Add regular physical activity like brisk walking",
            "Consider follow-up testing such as HbA1c",
        ],
    },
    ("Glucose", "Low"): {
        "risk": "Possible hypoglycemia, which can cause shakiness or fatigue.",
        "suggestions": [
            "Eat balanced meals at regular intervals",
            "Avoid skipping meals, especially breakfast",
        ],
    },
    ("HbA1c", "High"): {
        "risk": "Indicates higher average blood sugar, a possible diabetes risk marker.",
        "suggestions": [
            "Adopt a low-glycemic diet",
            "Increase physical activity",
            "Monitor blood sugar regularly and consult a doctor",
        ],
    },
    ("Vitamin D", "Deficient"): {
        "risk": "Possible bone health concerns and weakened immunity.",
        "suggestions": [
            "Get 15-20 minutes of safe sunlight exposure daily",
            "Include vitamin D-rich foods like eggs and fortified milk",
            "Consider a supplement after consulting a doctor",
        ],
    },
    ("Vitamin B12", "Deficient"): {
        "risk": "Possible nerve-related symptoms like tingling or fatigue.",
        "suggestions": [
            "Include dairy, eggs, and fortified cereals in your diet",
            "Consider B12 supplementation if you follow a plant-based diet",
        ],
    },
    ("Total Cholesterol", "High"): {
        "risk": "Possible increased risk of heart disease.",
        "suggestions": [
            "Reduce fried and processed foods",
            "Increase fiber intake with fruits, vegetables, and whole grains",
            "Exercise regularly",
        ],
    },
    ("LDL", "High"): {
        "risk": "Possible heart disease risk due to elevated 'bad' cholesterol.",
        "suggestions": [
            "Limit saturated and trans fats",
            "Walk regularly and stay active",
            "Increase soluble fiber intake (oats, beans)",
        ],
    },
    ("HDL", "Low"): {
        "risk": "Lower 'good' cholesterol may raise cardiovascular risk.",
        "suggestions": [
            "Include healthy fats like nuts, olive oil, and fatty fish",
            "Engage in regular aerobic exercise",
            "Avoid smoking",
        ],
    },
    ("Triglycerides", "High"): {
        "risk": "Possible increased cardiovascular risk.",
        "suggestions": [
            "Cut back on sugar and refined carbohydrates",
            "Limit alcohol intake",
            "Increase omega-3 rich foods like fish",
        ],
    },
    ("Creatinine", "High"): {
        "risk": "Possible reduced kidney function; needs medical follow-up.",
        "suggestions": [
            "Stay well hydrated",
            "Discuss with a doctor before taking NSAIDs or new supplements",
        ],
    },
    ("Uric Acid", "High"): {
        "risk": "Possible risk of gout or kidney stones.",
        "suggestions": [
            "Limit red meat, organ meat, and shellfish",
            "Reduce alcohol, especially beer",
            "Stay well hydrated",
        ],
    },
    ("Platelets", "Low"): {
        "risk": "Possible bleeding/clotting concerns; needs medical evaluation.",
        "suggestions": [
            "Avoid activities with high injury risk until evaluated",
            "Consult a doctor promptly for further tests",
        ],
    },
    ("WBC", "High"): {
        "risk": "May indicate infection or inflammation in the body.",
        "suggestions": [
            "Monitor for fever or other infection symptoms",
            "Follow up with a doctor for further evaluation",
        ],
    },
    ("WBC", "Low"): {
        "risk": "May indicate a weakened immune response.",
        "suggestions": [
            "Avoid exposure to infections where possible",
            "Consult a doctor for further evaluation",
        ],
    },
    ("TSH", "High"): {
        "risk": "Possible underactive thyroid (hypothyroidism).",
        "suggestions": [
            "Discuss thyroid function tests with a doctor",
            "Watch for symptoms like fatigue or weight gain",
        ],
    },
    ("TSH", "Low"): {
        "risk": "Possible overactive thyroid (hyperthyroidism).",
        "suggestions": [
            "Discuss thyroid function tests with a doctor",
            "Watch for symptoms like rapid heartbeat or weight loss",
        ],
    },
}
