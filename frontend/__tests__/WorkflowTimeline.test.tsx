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
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
    expect(screen.getByText("Approval")).toBeInTheDocument();
  });

  it("marks active step with aria-current=step", () => {
    render(<WorkflowTimeline steps={steps} />);
    const activeCircle = screen.getByRole("listitem", { hidden: true }).parentElement?.querySelector(
      '[aria-current="step"]',
    );
    // Alternatively check by text approach:
    const allCircles = document.querySelectorAll('[aria-current="step"]');
    expect(allCircles).toHaveLength(1);
  });

  it("shows checkmark for complete steps", () => {
    render(<WorkflowTimeline steps={steps} />);
    expect(screen.getByText("✓")).toBeInTheDocument();
  });

  it("renders nothing when steps is empty", () => {
    const { container } = render(<WorkflowTimeline steps={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders step role when provided", () => {
    const withRole: TimelineStep[] = [{ name: "Legal", status: "upcoming", role: "Legal Officer" }];
    render(<WorkflowTimeline steps={withRole} />);
    expect(screen.getByText("Legal Officer")).toBeInTheDocument();
  });

  it("renders connector lines between steps", () => {
    const { container } = render(<WorkflowTimeline steps={steps} />);
    // Each connector is an aria-hidden div
    const connectors = container.querySelectorAll('[aria-hidden="true"]');
    expect(connectors.length).toBe(steps.length - 1);
  });
});
