# SPDX-License-Identifier: MIT
"""Performance baseline measurement helpers for DocReview360 release readiness."""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable
from uuid import uuid4

from .approvals import approvals, create_approval, update_approval_state
from .documents import get_document, import_document


def _median(values: Iterable[float]) -> float:
    samples = list(values)
    if not samples:
        return 0.0
    if len(samples) == 1:
        return float(samples[0])
    return float(statistics.median(samples))


def measure_api_cold_start_seconds() -> float:
    """Measure API cold start via one-shot subprocess startup and health probe."""

    src_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    pythonpath_parts = [str(src_dir)]
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

    cmd = [
        sys.executable,
        "-c",
        (
            "from fastapi.testclient import TestClient;"
            "from docreview360.api import app;"
            "c=TestClient(app);"
            "r=c.get('/health');"
            "assert r.status_code==200"
        ),
    ]
    start = perf_counter()
    try:
        subprocess.run(
            cmd,
            check=True,
            env=env,
            capture_output=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive path
        stderr = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        raise RuntimeError(f"cold-start probe failed: {stderr}") from exc
    return perf_counter() - start


def _generate_fifty_page_markdown() -> bytes:
    page_blocks = []
    for page_number in range(1, 51):
        lines = [f"# Page {page_number}", ""]
        lines.extend(["DocReview360 performance baseline content line."] * 80)
        page_blocks.append("\n".join(lines))
    return "\n\f\n".join(page_blocks).encode("utf-8")


def measure_document_load_50_page_seconds() -> float:
    """Measure import+retrieve time for a representative 50-page markdown document."""

    payload = _generate_fifty_page_markdown()
    start = perf_counter()
    document = import_document(
        f"perf-baseline-{uuid4().hex}.md",
        payload,
        project="perf-baseline",
        user="perf",
    )
    loaded = get_document(document.id)
    if loaded is None:
        raise RuntimeError("document load benchmark failed to retrieve imported document")
    return perf_counter() - start


def measure_approval_transition_seconds() -> float:
    """Measure pending->rejected transition latency for one approval."""

    approvals.clear()
    approval = create_approval(
        workflow=f"wf-perf-{uuid4().hex}",
        reviewer="perf-reviewer",
        doc_id=f"doc-perf-{uuid4().hex}",
    )
    start = perf_counter()
    asyncio.run(update_approval_state(approval.id, "rejected"))
    return perf_counter() - start


async def _run_concurrency_transition(concurrency: int) -> float:
    approvals.clear()
    for index in range(concurrency):
        create_approval(
            workflow=f"wf-perf-concurrency-{uuid4().hex}",
            reviewer=f"reviewer-{index}",
            doc_id=f"doc-perf-concurrency-{index}-{uuid4().hex}",
        )

    start = perf_counter()
    await asyncio.gather(*[update_approval_state(appr.id, "rejected") for appr in approvals.values()])
    return perf_counter() - start


def measure_concurrency_transition_seconds(concurrency: int) -> float:
    """Measure aggregate transition time for ``concurrency`` simultaneous approvals."""

    if concurrency <= 0:
        raise ValueError("concurrency must be positive")
    return asyncio.run(_run_concurrency_transition(concurrency))


def collect_performance_baseline() -> dict[str, Any]:
    """Collect baseline performance metrics used for release documentation."""

    api_samples = [measure_api_cold_start_seconds() for _ in range(1)]
    document_samples = [measure_document_load_50_page_seconds() for _ in range(3)]
    transition_samples = [measure_approval_transition_seconds() for _ in range(5)]
    concurrency_10 = measure_concurrency_transition_seconds(10)
    concurrency_25 = measure_concurrency_transition_seconds(25)

    measured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "measured_at": measured_at,
        "api_cold_start_seconds": round(_median(api_samples), 4),
        "document_load_50_page_seconds": round(_median(document_samples), 4),
        "approval_transition_seconds": round(_median(transition_samples), 4),
        "concurrency": {
            "simultaneous_reviewers_10": {
                "total_seconds": round(concurrency_10, 4),
                "avg_transition_ms": round((concurrency_10 / 10.0) * 1000.0, 2),
            },
            "simultaneous_reviewers_25": {
                "total_seconds": round(concurrency_25, 4),
                "avg_transition_ms": round((concurrency_25 / 25.0) * 1000.0, 2),
            },
        },
    }


def write_performance_baseline_json(output_path: Path, payload: dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def write_performance_baseline_markdown(output_path: Path, payload: dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ten = payload["concurrency"]["simultaneous_reviewers_10"]
    twenty_five = payload["concurrency"]["simultaneous_reviewers_25"]

    lines = [
        "# Performance Baseline (v0.1)",
        "",
        f"Measured at (UTC): {payload['measured_at']}",
        "",
        "## Metrics",
        "",
        f"- API cold start (TestClient health probe): `{payload['api_cold_start_seconds']}s`",
        f"- 50-page document import+load time: `{payload['document_load_50_page_seconds']}s`",
        f"- Approval state transition latency (pending -> rejected): `{payload['approval_transition_seconds']}s`",
        f"- Concurrency (10 simultaneous reviewers): `{ten['total_seconds']}s` total, `{ten['avg_transition_ms']}ms` average transition",
        f"- Concurrency (25 simultaneous reviewers): `{twenty_five['total_seconds']}s` total, `{twenty_five['avg_transition_ms']}ms` average transition",
        "",
        "## Notes",
        "",
        "- This baseline is intended for release transparency, not synthetic peak benchmarking.",
        "- Re-run before each release candidate and record the generated JSON artifact.",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path

