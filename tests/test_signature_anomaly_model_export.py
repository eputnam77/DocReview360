from pathlib import Path
from uuid import uuid4

import pytest
from docreview360.ml.signature_anomaly import export_signature_anomaly_model

onnx = pytest.importorskip("onnx")


def test_export_signature_anomaly_model_ir_version() -> None:
    root = Path(__file__).resolve().parents[1]
    workspace_tmp = root / ".tmp" / "test-signature-anomaly"
    workspace_tmp.mkdir(parents=True, exist_ok=True)
    model_path = workspace_tmp / f"signature_anomaly-{uuid4().hex}.onnx"
    export_signature_anomaly_model(model_path)

    model = onnx.load_model(model_path)
    assert model.ir_version <= 11

    props = {item.key: item.value for item in model.metadata_props}
    assert props.get("docreview360:model") == "signature-anomaly"
    assert props.get("docreview360:version") == "1.0.0"
