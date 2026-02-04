from docreview360.guardrails import GuardrailThresholds, load_guardrail_thresholds


def test_guardrail_thresholds_ignore_non_finite() -> None:
    settings = {
        "documents": {
            "guardrails": {
                "quality": {"min_score": "nan", "flag_threshold": "inf"},
                "compliance": {"min_probability": "-inf"},
                "auto_assign": {
                    "editor": "ed",
                    "quality_below": "nan",
                    "compliance_below": "inf",
                },
            }
        }
    }
    thresholds = load_guardrail_thresholds(settings)
    defaults = GuardrailThresholds()

    assert thresholds.min_quality_score == defaults.min_quality_score
    assert thresholds.quality_flag_threshold == defaults.quality_flag_threshold
    assert thresholds.min_compliance_probability == defaults.min_compliance_probability
    assert thresholds.auto_assign_quality_below is None
    assert thresholds.auto_assign_compliance_below is None
    assert thresholds.auto_assign_editor == "ed"


def test_guardrail_thresholds_reject_out_of_range_values() -> None:
    settings = {
        "documents": {
            "guardrails": {
                "quality": {"min_score": 1.5, "flag_threshold": -0.25},
                "compliance": {"min_probability": 2},
                "auto_assign": {
                    "editor": "qa",
                    "quality_below": -0.1,
                    "compliance_below": 1.25,
                },
            }
        }
    }
    thresholds = load_guardrail_thresholds(settings)
    defaults = GuardrailThresholds()

    assert thresholds.min_quality_score == defaults.min_quality_score
    assert thresholds.quality_flag_threshold == defaults.quality_flag_threshold
    assert thresholds.min_compliance_probability == defaults.min_compliance_probability
    assert thresholds.auto_assign_quality_below is None
    assert thresholds.auto_assign_compliance_below is None
    assert thresholds.auto_assign_editor == "qa"


def test_guardrail_thresholds_ignore_boolean_values() -> None:
    settings = {
        "documents": {
            "guardrails": {
                "quality": {"min_score": True, "flag_threshold": False},
                "compliance": {"min_probability": True},
            }
        }
    }
    thresholds = load_guardrail_thresholds(settings)
    defaults = GuardrailThresholds()

    assert thresholds.min_quality_score == defaults.min_quality_score
    assert thresholds.quality_flag_threshold == defaults.quality_flag_threshold
    assert thresholds.min_compliance_probability == defaults.min_compliance_probability
