import numpy as np
import pytest

pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")

from docreview360.ml.onnx_infer import (
    clear_session_cache,
    get_model_metadata,
    get_session,
    infer,
)
from docreview360.ml.torch_models import build_clarity_critic, export_critic_to_onnx, train_critic


def test_export_and_infer(tmp_path):
    critic = build_clarity_critic()
    train_critic(critic, ["ok", "bad"], [0, 1], epochs=50, lr=0.05)
    model_path = tmp_path / "critic.onnx"
    meta = export_critic_to_onnx(
        critic,
        model_path,
        metadata={"docreview360:version": "test"},
    )
    assert model_path.exists()
    session = get_session(model_path)
    batch = np.zeros((2, critic.input_dim), dtype=np.float32)
    outputs = infer(session, {"input": batch})
    assert isinstance(outputs, list)
    assert outputs[0].shape == (2, 1)
    info = get_model_metadata(session)
    assert info.custom_metadata["docreview360:critic"] == critic.name
    assert info.custom_metadata["docreview360:version"] == "test"
    assert info.sha256 == meta["sha256"]


def test_quantize_flag(tmp_path):
    critic = build_clarity_critic()
    critic.reset_parameters("zeros")
    fp32_path = tmp_path / "fp32.onnx"
    int8_path = tmp_path / "int8.onnx"
    export_critic_to_onnx(critic, fp32_path)
    export_critic_to_onnx(critic, int8_path, quantize=True)
    assert int8_path.exists()
    info = get_model_metadata(int8_path)
    assert info.custom_metadata.get("docreview360:quantized") == "true"


def test_missing_execution_provider(tmp_path):
    clear_session_cache()
    critic = build_clarity_critic()
    model_path = tmp_path / "provider.onnx"
    export_critic_to_onnx(critic, model_path)
    with pytest.raises(RuntimeError) as excinfo:
        get_session(model_path, providers=["ImaginaryExecutionProvider"])
    assert "Missing execution providers" in str(excinfo.value)
