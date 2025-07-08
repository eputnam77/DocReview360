"""Workflow UI components bundle (Task 160)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .stubs import record_task_completion


@dataclass
class StepInstance:
    """Single workflow step and its status."""

    name: str
    status: str = "pending"


@dataclass
class WorkflowInstance:
    """Simple workflow instance with ordered steps."""

    id: str
    steps: List[StepInstance]
    current: int = 0


MOCK_STEPS = [StepInstance("draft"), StepInstance("review"), StepInstance("approved")]
MOCK_INSTANCE = WorkflowInstance(id="wf1", steps=MOCK_STEPS)


class UploadDropzone:
    """Placeholder upload dropzone component."""

    def render(self) -> str:
        record_task_completion(160)
        return "<div class='upload-dropzone'></div>"


class ProgressSidebar:
    """Placeholder progress sidebar component."""

    def render(self, workflow: WorkflowInstance) -> str:
        record_task_completion(160)
        steps = ",".join(step.name for step in workflow.steps)
        return f"<aside data-steps='{steps}' data-current='{workflow.current}'></aside>"


class CompletedBanner:
    """Placeholder completed banner component."""

    def render(self, workflow: WorkflowInstance) -> str:
        record_task_completion(160)
        return f"<div class='completed'>{workflow.id}</div>"


class StepStatusBadge:
    """Placeholder step status badge component."""

    def render(self, step: StepInstance) -> str:
        record_task_completion(160)
        return f"<span class='badge {step.status}'></span>"
