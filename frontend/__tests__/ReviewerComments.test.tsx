import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ReviewerComments from "../components/ReviewerComments";

// Stable mock data
const { stableComments } = vi.hoisted(() => ({
  stableComments: [
    {
      id: "c1",
      document: "doc1",
      user: "alice",
      text: "Legal concern noted",
      raw_text: "Legal concern noted",
      mentions: [],
      parent: null,
      created: "2024-01-01T10:00:00Z",
      tags: ["legal"],
      status: "open" as const,
    },
    {
      id: "c2",
      document: "doc1",
      user: "bob",
      text: "Reply to legal",
      raw_text: "Reply to legal",
      mentions: [],
      parent: "c1",
      created: "2024-01-01T11:00:00Z",
      tags: [],
      status: "open" as const,
    },
    {
      id: "c3",
      document: "doc1",
      user: "carol",
      text: "Style issue",
      raw_text: "Style issue",
      mentions: [],
      parent: null,
      created: "2024-01-01T12:00:00Z",
      tags: ["style"],
      status: "resolved" as const,
    },
  ],
}));

vi.mock("@/lib/useComments", () => ({
  useComments: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  API: "http://localhost:8000",
  authenticatedFetch: vi.fn(),
}));

vi.mock("react-hot-toast", () => ({
  default: { error: vi.fn(), success: vi.fn() },
  toast: { error: vi.fn(), success: vi.fn() },
}));

import { useComments } from "@/lib/useComments";

const mockUseComments = vi.mocked(useComments);
const mockPostComment = vi.fn();
const mockUpdateComment = vi.fn();

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("ReviewerComments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseComments.mockReturnValue({
      comments: stableComments,
      isLoading: false,
      postComment: mockPostComment,
      updateComment: mockUpdateComment,
      isPosting: false,
      isUpdating: false,
    });
  });

  it("renders parent comments", () => {
    render(<ReviewerComments docId="doc1" currentUser="alice" />, { wrapper });
    expect(screen.getByText("Legal concern noted")).toBeTruthy();
    expect(screen.getByText("Style issue")).toBeTruthy();
  });

  it("renders replies indented under parent", () => {
    render(<ReviewerComments docId="doc1" currentUser="alice" />, { wrapper });
    expect(screen.getByText("Reply to legal")).toBeTruthy();
  });

  it("shows tag chips for tagged comments", () => {
    render(<ReviewerComments docId="doc1" currentUser="alice" />, { wrapper });
    // "legal" appears as a tag chip on comment c1 AND as a form tag button — use getAllByText
    expect(screen.getAllByText("legal").length).toBeGreaterThan(0);
    expect(screen.getAllByText("style").length).toBeGreaterThan(0);
  });

  it("shows status badge for each parent comment", () => {
    render(<ReviewerComments docId="doc1" currentUser="alice" />, { wrapper });
    // Two parent comments: one "open", one "resolved"
    const openBadges = screen.getAllByText("open");
    expect(openBadges.length).toBeGreaterThan(0);
    expect(screen.getByText("resolved")).toBeTruthy();
  });

  it("shows Resolve/Accept/Reject buttons when canDispose=true and comment is open", () => {
    render(<ReviewerComments docId="doc1" currentUser="alice" canDispose />, { wrapper });
    expect(screen.getAllByText("Resolve").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Accept").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Reject").length).toBeGreaterThan(0);
  });

  it("hides disposition buttons when canDispose=false", () => {
    render(<ReviewerComments docId="doc1" currentUser="alice" canDispose={false} />, { wrapper });
    expect(screen.queryByText("Resolve")).toBeFalsy();
  });

  it("calls updateComment with resolved when Resolve is clicked", async () => {
    mockUpdateComment.mockResolvedValue({});
    render(<ReviewerComments docId="doc1" currentUser="alice" canDispose />, { wrapper });
    fireEvent.click(screen.getAllByText("Resolve")[0]);
    await waitFor(() =>
      expect(mockUpdateComment).toHaveBeenCalledWith("c1", { status: "resolved" }),
    );
  });

  it("submits a new comment on form submit", async () => {
    mockPostComment.mockResolvedValue({});
    render(<ReviewerComments docId="doc1" currentUser="alice" />, { wrapper });

    const textarea = screen.getByPlaceholderText("Add a comment…");
    fireEvent.change(textarea, { target: { value: "My new comment" } });
    fireEvent.submit(textarea.closest("form")!);

    await waitFor(() =>
      expect(mockPostComment).toHaveBeenCalledWith(
        expect.objectContaining({ text: "My new comment", user: "alice" }),
      ),
    );
  });

  it("includes selected tags in submitted comment", async () => {
    mockPostComment.mockResolvedValue({});
    render(<ReviewerComments docId="doc1" currentUser="alice" />, { wrapper });

    fireEvent.change(screen.getByPlaceholderText("Add a comment…"), {
      target: { value: "Policy note" },
    });
    // Click the "policy" tag chip — it only appears in the form (not in any comment tag)
    fireEvent.click(screen.getByRole("button", { name: "policy" }));
    fireEvent.submit(screen.getByPlaceholderText("Add a comment…").closest("form")!);

    await waitFor(() =>
      expect(mockPostComment).toHaveBeenCalledWith(
        expect.objectContaining({ tags: ["policy"] }),
      ),
    );
  });

  it("shows loading state", () => {
    mockUseComments.mockReturnValue({
      comments: [],
      isLoading: true,
      postComment: mockPostComment,
      updateComment: mockUpdateComment,
      isPosting: false,
      isUpdating: false,
    });
    render(<ReviewerComments docId="doc1" currentUser="alice" />, { wrapper });
    expect(screen.getByText("Loading comments…")).toBeTruthy();
  });

  it("shows empty state when no comments", () => {
    mockUseComments.mockReturnValue({
      comments: [],
      isLoading: false,
      postComment: mockPostComment,
      updateComment: mockUpdateComment,
      isPosting: false,
      isUpdating: false,
    });
    render(<ReviewerComments docId="doc1" currentUser="alice" />, { wrapper });
    expect(screen.getByText(/No comments yet/)).toBeTruthy();
  });
});
