import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import WorkflowTimeline from "../components/WorkflowTimeline";
import type { TimelineStep } from "../components/WorkflowTimeline";

const steps: TimelineStep[] = [
  { name: "Draft", status: "complete" },
  { name: "Review", status: "active" },
  { name: "Approval", status: "upcoming" },
];

describe("WorkflowTimeline", () => {
  it("renders all step names", () => {
    render(<WorkflowTimeline steps={steps} />);
    expect(screen.getByText("Draft")).toBeTruthy();
    expect(screen.getByText("Review")).toBeTruthy();
    expect(screen.getByText("Approval")).toBeTruthy();
  });

  it("marks active step with aria-current=step", () => {
    render(<WorkflowTimeline steps={steps} />);
    const allCurrent = document.querySelectorAll('[aria-current="step"]');
    expect(allCurrent).toHaveLength(1);
  });

  it("shows checkmark for complete steps", () => {
    render(<WorkflowTimeline steps={steps} />);
    expect(screen.getByText("✓")).toBeTruthy();
  });

  it("renders nothing when steps is empty", () => {
    const { container } = render(<WorkflowTimeline steps={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders step role when provided", () => {
    const withRole: TimelineStep[] = [{ name: "Legal", status: "upcoming", role: "Legal Officer" }];
    render(<WorkflowTimeline steps={withRole} />);
    expect(screen.getByText("Legal Officer")).toBeTruthy();
  });

  it("renders connector lines between steps", () => {
    const { container } = render(<WorkflowTimeline steps={steps} />);
    // Each connector is an aria-hidden div
    const connectors = container.querySelectorAll('[aria-hidden="true"]');
    expect(connectors.length).toBe(steps.length - 1);
  });
});
