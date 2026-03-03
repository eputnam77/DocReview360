import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import TemplatesIndex, { createTemplateConfigApi } from "../pages/configuration/templates/index";

// Stable mock data hoisted to avoid infinite re-render loops
const { pendingTemplate, approvedTemplate } = vi.hoisted(() => ({
  pendingTemplate: {
    id: "tpl-1",
    name: "Draft Template",
    docType: "Policy",
    format: "HTML",
    modified: "2024-01-01",
    approved: false,
    retired: false,
  },
  approvedTemplate: {
    id: "tpl-2",
    name: "Approved Template",
    docType: "Policy",
    format: "DOCX",
    modified: "2024-01-02",
    approved: true,
    retired: false,
  },
}));

vi.mock("@/lib/api", () => ({
  API: "http://localhost:8000",
  authenticatedFetch: vi.fn(),
}));

vi.mock("react-hot-toast", () => ({
  default: { error: vi.fn(), success: vi.fn() },
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.PropsWithChildren<{ href: string }>) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

import { authenticatedFetch } from "@/lib/api";

const mockFetch = vi.mocked(authenticatedFetch);

function makeListResponse(templates: object[]) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(templates),
  } as Response);
}

function makeOkResponse() {
  return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
}

describe("TemplatesIndex – approve/retire buttons", () => {
  beforeEach(() => {
    // resetAllMocks clears both call history AND the mockResolvedValueOnce queue,
    // preventing queue contamination from pending async ops in previous tests.
    vi.resetAllMocks();
    // First call: listTemplates; second call: listEmailTemplates
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([pendingTemplate, approvedTemplate]),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      } as Response);
  });

  it("shows Approve button for pending (unapproved) template", async () => {
    render(<TemplatesIndex />);
    await waitFor(() => screen.getByText("Draft Template"));
    expect(screen.getByRole("button", { name: "Approve template" })).toBeTruthy();
  });

  it("shows Retire button for approved template", async () => {
    render(<TemplatesIndex />);
    await waitFor(() => screen.getByText("Approved Template"));
    expect(screen.getByRole("button", { name: "Retire template" })).toBeTruthy();
  });

  it("does not show Approve for already-approved template", async () => {
    render(<TemplatesIndex />);
    await waitFor(() => screen.getByText("Approved Template"));
    const approveBtns = screen.queryAllByRole("button", { name: "Approve template" });
    // Only one Approve button (for the pending template), not for approved one
    expect(approveBtns).toHaveLength(1);
  });

  it("calls approve endpoint on Approve button click", async () => {
    // After approve, reload
    mockFetch
      .mockResolvedValueOnce(makeOkResponse()) // approve POST
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([{ ...pendingTemplate, approved: true }]),
      } as Response) // reload listTemplates
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) } as Response); // reload emailTemplates

    render(<TemplatesIndex />);
    await waitFor(() => screen.getByText("Draft Template"));

    fireEvent.click(screen.getByRole("button", { name: "Approve template" }));

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/templates/tpl-1/approve"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("calls retire endpoint on Retire button click", async () => {
    render(<TemplatesIndex />);
    // Wait for initial render (mocks 1 & 2 from beforeEach consumed here)
    await waitFor(() => screen.getByRole("button", { name: "Retire template" }));

    // Now add extra mocks for the retire POST + reload
    mockFetch
      .mockResolvedValueOnce(makeOkResponse()) // retire POST
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      } as Response) // reload listTemplates
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) } as Response); // reload email

    fireEvent.click(screen.getByRole("button", { name: "Retire template" }));

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/templates/tpl-2/retire"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});

describe("createTemplateConfigApi", () => {
  it("exposes approveTemplate and retireTemplate methods", () => {
    const api = createTemplateConfigApi();
    expect(typeof api.approveTemplate).toBe("function");
    expect(typeof api.retireTemplate).toBe("function");
  });
});
