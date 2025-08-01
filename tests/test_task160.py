from pathlib import Path

from docreview360.stubs.task160 import task160


def test_task160_components_bundle() -> None:
    """Verify workflow components bundle is available."""

    task160()

    # Use paths relative to project root
    project_root = Path(__file__).parent.parent
    wf_dir = project_root / "frontend" / "components" / "workflow"
    assert (wf_dir / "UploadDropzone.tsx").exists()
    assert (wf_dir / "ProgressSidebar.tsx").exists()
    assert (wf_dir / "CompletedBanner.tsx").exists()
    assert (wf_dir / "StepStatusBadge.tsx").exists()

    index_src = (wf_dir / "index.ts").read_text()
    assert "UploadDropzone" in index_src

    types_src = (project_root / "frontend" / "types.ts").read_text()
    assert "interface StepInstance" in types_src

    data_src = (project_root / "frontend" / "data" / "mock.ts").read_text()
    assert "MOCK_INSTANCE" in data_src
