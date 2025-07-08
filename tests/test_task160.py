from pathlib import Path

from docuflow.stubs.task160 import task160


def test_task160_components_bundle() -> None:
    """Verify workflow components bundle is available."""

    task160()

    wf_dir = Path("frontend/components/workflow")
    assert (wf_dir / "UploadDropzone.tsx").exists()
    assert (wf_dir / "ProgressSidebar.tsx").exists()
    assert (wf_dir / "CompletedBanner.tsx").exists()
    assert (wf_dir / "StepStatusBadge.tsx").exists()

    index_src = (wf_dir / "index.ts").read_text()
    assert "UploadDropzone" in index_src

    types_src = Path("frontend/types.ts").read_text()
    assert "interface StepInstance" in types_src

    data_src = Path("frontend/data/mock.ts").read_text()
    assert "MOCK_INSTANCE" in data_src
