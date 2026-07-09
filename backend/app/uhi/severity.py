from .classification import DEFAULT_SEVERITY_CLASSES, SEVERITY_ORDER, classify_severity

SEVERITY_COLORS: dict[str, str] = {
    "Very Low": "#2c7bb6",
    "Low": "#abd9e9",
    "Moderate": "#ffffbf",
    "High": "#fdae61",
    "Very High": "#f46d43",
    "Extreme": "#d7191c",
}

SEVERITY_RECOMMENDATIONS: dict[str, list[str]] = {
    "Very Low": [],
    "Low": [
        "Monitor temperature trends",
        "Maintain existing vegetation cover",
    ],
    "Moderate": [
        "Increase tree canopy coverage",
        "Install green roofs on new buildings",
        "Review urban planning guidelines",
    ],
    "High": [
        "Prioritize area for cooling interventions",
        "Implement cool roof program",
        "Establish urban cooling center",
        "Increase albedo of paved surfaces",
    ],
    "Very High": [
        "Immediate heat action plan required",
        "Deploy emergency cooling measures",
        "Accelerate green infrastructure investment",
        "Establish heat warning system",
        "Conduct community outreach",
    ],
    "Extreme": [
        "Emergency heat response activation",
        "Mandatory cooling requirements",
        "Expedite green infrastructure deployment",
        "Implement heat emergency protocols",
        "Mobilize community health resources",
        "Consider emergency shade structures",
    ],
}
