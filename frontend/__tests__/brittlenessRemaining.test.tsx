import React from "react";
import { readFileSync } from "fs";
import { join } from "path";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import ApprovalTable from "@/components/ApprovalTable";

vi.mock("react-hot-toast", () => ({
  toast: Object.assign(vi.fn(), { success: vi.fn() }),
}));

const REPO_ROOT = join(process.cwd());
const FRONTEND_ROOT = REPO_ROOT.endsWith("frontend") ? REPO_ROOT : join(REPO_ROOT, "frontend");
const lib = (name: string) => readFileSync(join(FRONTEND_ROOT, "lib", name), "utf8");
const page = (...parts: string[]) => readFileSync(join(FRONTEND_ROOT, "pages", ...parts), "utf8");
const projectComp = (name: string) =>
  readFileSync(join(FRONTEND_ROOT, "components/project", name), "utf8");

function makeApproval(index: number) {
  return {
    id: `approval-${index}`,
    reviewer: `reviewer-${index}`,
    email: `reviewer-${index}@example.com`,
    state: "pending",
    dueAt: null,
    signedAt: null,
    required: true,
    role: "Approver",
    description: `Approval ${index}`,
  } as any;
}

describe("Remaining brittleness findings", () => {
  it("F-01 extracts project page sections into dedicated components", () => {
    const projectPage = page("projects", "[id]", "index.tsx");
    expect(projectPage).toContain("ApprovalsTab");
    expect(projectPage).toContain("LifecycleTab");
    expect(projectPage).toContain("FeedbackTab");
    expect(projectPage).toContain("NaraTab");
    expect(projectPage).toContain("SlaTab");
    expect(projectPage).toContain("AuditTab");
    expect(projectComp("ApprovalsTab.tsx")).toContain("id=\"approvals\"");
    expect(projectComp("LifecycleTab.tsx")).toContain("id=\"reviewers\"");
    expect(projectComp("FeedbackTab.tsx")).toContain("id=\"feedback\"");
    expect(projectComp("AuditTab.tsx")).toContain("id=\"history\"");
  });

  it("F-02 splits project detail queries into dedicated hooks", () => {
    const src = lib("useProjectPageData.ts");
    const hookSrc = lib("projectPageDataHooks.ts");
    expect(src).toContain("useProjectReviewCycleData");
    expect(src).toContain("useProjectFeedbackData");
    expect(src).toContain("useProjectDocumentScores");
    expect(src).toContain("useProjectVersionHistory");
    expect(src).toContain("useProjectFSVStatus");
    expect(hookSrc).toContain("export function useProjectReviewCycleData");
    expect(hookSrc).toContain("export function useProjectFeedbackData");
  });

  it("F-03 splits editor extension state into focused sub-hooks", () => {
    const src = lib("useEditorExtensions.ts");
    expect(src).toContain("useEditorCollab");
    expect(src).toContain("useEditorLint");
    expect(src).toContain("useEditorOptionalExtensions");
    expect(src).toContain("Keep collaboration provider lifecycle out of render");
    expect(lib("useEditorCollab.ts")).toContain("export function useEditorCollab");
    expect(lib("useEditorLint.ts")).toContain("export function useEditorLint");
    expect(lib("useEditorOptionalExtensions.ts")).toContain(
      "export function useEditorOptionalExtensions",
    );
  });

  it("F-13 adds loading and retry states to remaining configuration pages", () => {
    expect(page("configuration", "phases.tsx")).toContain("isLoading");
    expect(page("configuration", "phases.tsx")).toContain("fetchError");
    expect(page("configuration", "permissions.tsx")).toContain("isLoading");
    expect(page("configuration", "permissions.tsx")).toContain("fetchError");
    expect(page("configuration", "workflows", "new.tsx")).toContain("isLoading");
    expect(page("configuration", "workflows", "new.tsx")).toContain("fetchError");
  });

  it("F-15 imports react-window and renders virtualization for large approval sets", () => {
    const src = readFileSync(
      join(FRONTEND_ROOT, "components/ApprovalTable.tsx"),
      "utf8",
    );
    expect(src).toContain("FixedSizeList");
    expect(src).toContain("approval-table-virtualized");

    render(
      <ApprovalTable
        approvals={Array.from({ length: 60 }, (_, index) => makeApproval(index))}
        currentUser="reviewer-0"
        canEdit
        handlers={{
          onAssign: vi.fn(),
          onSign: vi.fn(),
          onReject: vi.fn(),
          onSignInitials: vi.fn(),
          onReset: vi.fn(),
          onRemove: vi.fn(),
          onBulkReminder: vi.fn(),
          onHistory: vi.fn(),
        }}
      />,
    );

    expect(screen.getByTestId("approval-table-virtualized")).toBeTruthy();
  });

  it("does not mark reviewer sign-off as phase-ready while approvals are incomplete", () => {
    const projectPage = page("projects", "[id]", "index.tsx");
    expect(projectPage).toContain(
      "Reviewer Sign-off Complete - Required Approvals Pending",
    );
    expect(projectPage).toContain("disabled={!canAdvance}");
    expect(projectPage).toContain(
      "All required approvals must be complete before advancing",
    );
  });

  it("shows username approvers even when reviewer equals role", () => {
    render(
      <ApprovalTable
        approvals={[
          {
            id: "approval-alice",
            reviewer: "alice",
            email: "alice@example.com",
            state: "pending",
            dueAt: null,
            signedAt: null,
            required: true,
            role: "alice",
            description: "Review Approval",
          } as any,
        ]}
        currentUser="bob"
        canEdit
        reviewerOptions={["alice", "bob"]}
        handlers={{
          onAssign: vi.fn(),
          onSign: vi.fn(),
          onReject: vi.fn(),
          onSignInitials: vi.fn(),
          onReset: vi.fn(),
          onRemove: vi.fn(),
          onBulkReminder: vi.fn(),
          onHistory: vi.fn(),
        }}
      />,
    );

    expect(screen.queryByText("Unassigned")).toBeNull();
    expect(screen.getAllByText("alice").length).toBeGreaterThanOrEqual(2);
  });

  it("keeps workflow role placeholders unassigned even when they appear as options", () => {
    render(
      <ApprovalTable
        approvals={[
          {
            id: "approval-sme",
            reviewer: "SME",
            email: "sme@example.com",
            state: "pending",
            dueAt: null,
            signedAt: null,
            required: true,
            role: "SME",
            description: "Subject Matter Expert review and validation",
          } as any,
        ]}
        currentUser="bob"
        canEdit
        reviewerOptions={["alice", "bob", "SME"]}
        handlers={{
          onAssign: vi.fn(),
          onSign: vi.fn(),
          onReject: vi.fn(),
          onSignInitials: vi.fn(),
          onReset: vi.fn(),
          onRemove: vi.fn(),
          onBulkReminder: vi.fn(),
          onHistory: vi.fn(),
        }}
      />,
    );

    expect(screen.getByText("Unassigned")).toBeTruthy();
  });

  it("renders future approvals without exposing approval actions", () => {
    render(
      <ApprovalTable
        approvals={[
          {
            id: "approval-future",
            reviewer: "alice",
            email: "alice@example.com",
            state: "future",
            dueAt: null,
            signedAt: null,
            required: true,
            role: "Technical Writer",
            description: "Future sequential approval",
          } as any,
        ]}
        currentUser="alice"
        canEdit
        reviewerOptions={["alice", "bob"]}
        handlers={{
          onAssign: vi.fn(),
          onSign: vi.fn(),
          onReject: vi.fn(),
          onSignInitials: vi.fn(),
          onReset: vi.fn(),
          onRemove: vi.fn(),
          onBulkReminder: vi.fn(),
          onHistory: vi.fn(),
        }}
      />,
    );

    expect(screen.getByText("future")).toBeTruthy();
    expect(
      screen.getByText((text) => text.includes("Future 1") && text.includes("Pending 0")),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
  });
});
