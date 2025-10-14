from docreview360.ml.pytorch_migration_plan import WORKSTREAMS


def test_expected_workstreams_present():
    expected_keys = {
        "quality_critic_model",
        "template_compliance_classifier",
        "reviewer_routing_model",
        "signature_anomaly_model",
        "model_shim",
        "feature_adapters",
        "serving_endpoints",
        "dashboards_analytics",
        "guardrails_middleware",
        "cli_tooling",
        "testing_operations",
        "optional_helpers",
    }
    assert expected_keys == set(WORKSTREAMS), "Workstream keys mismatch"


def test_each_workstream_has_tasks_tests_and_docs():
    for key, workstream in WORKSTREAMS.items():
        assert workstream.tasks, f"{key} missing tasks"
        assert workstream.tests, f"{key} missing tests"
        assert workstream.documentation, f"{key} missing documentation"


def test_integration_points_accounted_for():
    api_tasks = WORKSTREAMS["serving_endpoints"].tasks
    assert any("/ml/score-quality" in task for task in api_tasks)
    guardrail_tasks = WORKSTREAMS["guardrails_middleware"].tasks
    assert any("threshold" in task.lower() for task in guardrail_tasks)
    cli_tasks = WORKSTREAMS["cli_tooling"].tasks
    assert any("ml-train" in task for task in cli_tasks)


def test_optional_helper_mentions_quantization_and_spacy():
    helper_tasks = " ".join(WORKSTREAMS["optional_helpers"].tasks).lower()
    assert "spacy" in helper_tasks
    assert "quantization" in helper_tasks
