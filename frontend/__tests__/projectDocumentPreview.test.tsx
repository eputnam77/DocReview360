/**
 * Tests for:
 *  1. Document preview panels on the Feedback and Signatures tabs (Section 44, items 1 & 2)
 *  2. Jump-to-location button on inline feedback items (Section 44, item 6)
 */
import React, { act } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProjectDetailsPage from "../pages/projects/[id]";
import { useUserStore } from "@/state/user";

const approvalTableSpy = vi.fn();

const routerPushMock = vi.fn();

// Stable mock data — all in vi.hoisted() so factories can reference them safely
const {
  stableProject,
  stableWorkflow,
  stableApprovals,
  stableReviewSummary,
  inlineFeedbackItem,
  manualFeedbackItem,
} = vi.hoisted(() => {
  const proj = {
    id: "proj-preview",
    number: "AC-02",
    type: "Test",
    title: "Preview Test Project",
    owner: "alice",
    status: "In Progress",
    progress: 30,
    updated: "2024-01-01",
    editor: "tiptap",
    currentPhaseId: "Review",
    workflow: "workflow-1",
  };
  const workflow = {
    id: "workflow-1",
    phase: "Review",
    steps: [
      { name: "Draft", status: "complete" },
      { name: "Review", status: "active" },
    ],
  };
  const inline = {
    id: "fb-inline-1",
    reviewer: "alice",
    feedback_type: "comment",
    text: "This paragraph needs clarification",
    phase: "Review",
    status: "open",
    created_at: "2024-01-05T10:00:00Z",
    disposition_by: null,
    disposition_at: null,
    disposition_reason: null,
    parent_id: null,
    tags: [],
    question_satisfied: false,
    assignment_id: null,
    source: "inline",
    range_anchor: "42:57",
  };
  const manual = {
    id: "fb-manual-1",
    reviewer: "bob",
    feedback_type: "suggestion",
    text: "Consider adding more detail here",
    phase: "Review",
    status: "open",
    created_at: "2024-01-06T10:00:00Z",
    disposition_by: null,
    disposition_at: null,
    disposition_reason: null,
    parent_id: null,
    tags: [],
    question_satisfied: false,
    assignment_id: null,
    source: null,
    range_anchor: null,
  };
  return {
    stableProject: proj,
    stableWorkflow: workflow,
    stableApprovals: [] as any[],
    stableReviewSummary: { count: 0 },
    inlineFeedbackItem: inline,
    manualFeedbackItem: manual,
  };
});

const { useUserStoreMock, defaultUserState } = vi.hoisted(() => {
  const defaultState = {
    username: "alice",
    isAdmin: true,
    isAuditor: false,
  };
  const store = { ...defaultState };
  const hook: any = (selector: (state: typeof store) => unknown) => selector(store);
  hook.setState = (partial: Partial<typeof store>) => {
    Object.assign(store, partial);
  };
  hook.getState = () => store;
  hook.reset = () => {
    Object.assign(store, defaultState);
  };
  return { useUserStoreMock: hook, defaultUserState: defaultState };
});

vi.mock("@/state/user", () => ({ useUserStore: useUserStoreMock }));

vi.mock("next/router", () => ({
  useRouter: () => ({
    query: { id: "proj-preview" },
    isReady: true,
    push: routerPushMock,
    replace: vi.fn(),
  }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.PropsWithChildren<{ href?: string; [key: string]: unknown }>) => (
    <a href={href as string} {...props}>{children}</a>
  ),
}));

vi.mock("lucide-react", () => {
  const React = require("react");
  const Icon = ({ className }: { className?: string }) =>
    React.createElement("span", { className });
  return {
    FileEdit: Icon,
    History: Icon,
    LayoutList: Icon,
    Download: Icon,
    Mail: Icon,
    Users2: Icon,
    UserPlus: Icon,
    Pencil: Icon,
    Trash2: Icon,
    CheckCircle2: Icon,
    XCircle: Icon,
    Clock: Icon,
    MessageSquare: Icon,
    HelpCircle: Icon,
    Lightbulb: Icon,
    AlertTriangle: Icon,
    ChevronDown: Icon,
    ChevronRight: Icon,
    Bell: Icon,
    MapPin: Icon,
    PanelRightOpen: Icon,
    PanelRightClose: Icon,
  };
});

function primitiveStub(tag: keyof React.JSX.IntrinsicElements) {
  return React.forwardRef<HTMLElement, React.PropsWithChildren<Record<string, unknown>>>(
    ({ children, ...props }, ref) => React.createElement(tag, { ...props, ref }, children),
  );
}

vi.mock("@/components", () => {
  const React = require("react");
  return {
    ApprovalTable: (props: Record<string, unknown>) => {
      approvalTableSpy(props);
      return React.createElement("div", { "data-testid": "approval-table" });
    },
    AuditTimeline: () => React.createElement("div", { "data-testid": "audit-timeline" }),
    ProjectSummaryBar: () => React.createElement("div", null),
    KpiCards: () => React.createElement("div", null),
    PhaseAdvanceModal: () => React.createElement("div", null),
    WorkflowTimeline: () => React.createElement("div", null),
    ReviewerComments: () => React.createElement("div", { "data-testid": "reviewer-comments" }),
    UserPicker: () => React.createElement("div", null),
    HelpTooltip: ({ children }: React.PropsWithChildren) =>
      React.createElement("span", null, children),
  };
});

vi.mock("@/components/ui/button", () => ({
  Button: primitiveStub("button"),
}));

vi.mock("@/components/ui/card", () => ({
  Card: primitiveStub("div"),
  CardContent: primitiveStub("div"),
  CardHeader: primitiveStub("div"),
  CardTitle: primitiveStub("div"),
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: primitiveStub("div"),
  DialogContent: primitiveStub("div"),
  DialogHeader: primitiveStub("div"),
  DialogTitle: primitiveStub("div"),
}));

vi.mock("@/components/ui/table", () => ({
  Table: primitiveStub("table"),
  TableHeader: primitiveStub("thead"),
  TableBody: primitiveStub("tbody"),
  TableRow: primitiveStub("tr"),
  TableHead: primitiveStub("th"),
  TableCell: primitiveStub("td"),
}));

vi.mock("@headlessui/react", () => {
  const React = require("react");
  const DisclosureContext = React.createContext<any>(null);
  const Disclosure: any = ({ children, defaultOpen = false }: any) => {
    const [open, setOpen] = React.useState(defaultOpen);
    const toggle = React.useCallback(() => setOpen((v: boolean) => !v), []);
    const ctx = React.useMemo(() => ({ open, toggle }), [open, toggle]);
    const rendered = typeof children === "function" ? children({ open }) : children;
    return React.createElement(DisclosureContext.Provider, { value: ctx }, rendered);
  };
  Disclosure.Button = React.forwardRef(({ children, onClick, ...props }: any, ref: any) => {
    const ctx = React.useContext(DisclosureContext);
    const handleClick = (e: any) => { ctx?.toggle(); onClick?.(e); };
    return React.createElement("button", { ...props, onClick: handleClick, ref }, children);
  });
  const Transition = ({ show = true, as: Comp = React.Fragment, children }: any) => {
    if (!show) return null;
    const resolved = typeof children === "function" ? children({}) : children;
    return React.createElement(Comp, null, resolved);
  };
  return { Disclosure, Transition };
});

vi.mock("@/lib/api", () => ({
  API: "http://example.com",
  authenticatedFetch: vi.fn().mockImplementation((url: string) => {
    if (url.includes("/feedback/progress")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({ total: 2, open: 1, accepted: 1, rejected: 0, resolved: 0, addressed: 1, by_type: {} }),
      });
    }
    if (url.includes("/feedback")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({ items: [inlineFeedbackItem, manualFeedbackItem], total: 2, skip: 0, limit: 20 }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  }),
}));

vi.mock("@/lib/useProject", () => ({
  useProject: () => ({ data: stableProject, isLoading: false }),
}));

vi.mock("@/lib/usePhases", () => ({
  usePhases: () => ({ data: stableWorkflow, isLoading: false }),
}));

vi.mock("@/lib/useApprovals", () => ({
  useApprovals: () => ({
    approvals: stableApprovals,
    approve: vi.fn(),
    reset: vi.fn(),
    remind: vi.fn(),
    isLoading: false,
  }),
}));

vi.mock("@/lib/useReviewSummary", () => ({
  useReviewSummary: () => ({ data: stableReviewSummary, isLoading: false }),
}));

vi.mock("@/lib/useProjectReviewers", () => ({
  useProjectReviewers: () => ({
    reviewers: [],
    isLoading: false,
    error: null,
    addReviewer: vi.fn(),
    updateReviewer: vi.fn(),
    removeReviewer: vi.fn(),
  }),
}));

vi.mock("react-hot-toast", () => {
  const toast = Object.assign(vi.fn(), { error: vi.fn(), success: vi.fn() });
  return { toast };
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProjectDetailsPage />
    </QueryClientProvider>,
  );
}

async function openCommentsSection() {
  fireEvent.click(screen.getByTestId("comments-section-toggle"));
  await waitFor(() => {
    expect(screen.getByTestId("feedback-preview-toggle")).toBeDefined();
  });
}

async function openReviewerSection() {
  fireEvent.click(screen.getByTestId("reviewer-signoff-section-toggle"));
  await waitFor(() => {
    expect(screen.getByTestId("signatures-preview-toggle")).toBeDefined();
  });
}

describe("Document preview panel", () => {
  beforeEach(() => {
    approvalTableSpy.mockClear();
    useUserStore.setState({ ...defaultUserState });
  });

  it("feedback preview panel is hidden by default and toggles open on button click", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("comments-section-toggle")).toBeDefined();
    });
    await openCommentsSection();

    // The feedback preview toggle button should be rendered
    const toggleButton = screen.getByTestId("feedback-preview-toggle");
    expect(toggleButton).toBeDefined();

    // Panel should not be visible initially
    expect(screen.queryByTestId("feedback-preview-panel")).toBeNull();

    // Click the toggle to open the preview
    await act(async () => {
      fireEvent.click(toggleButton);
    });

    // Panel should now be visible
    await waitFor(() => {
      expect(screen.getByTestId("feedback-preview-panel")).toBeDefined();
    });

    // Click the toggle again to close the preview
    const toggleAfterOpen = screen.getByTestId("feedback-preview-toggle");
    await act(async () => {
      fireEvent.click(toggleAfterOpen);
    });

    await waitFor(() => {
      expect(screen.queryByTestId("feedback-preview-panel")).toBeNull();
    });
  });

  it("signatures preview panel is hidden by default and toggles open on button click", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("reviewer-signoff-section-toggle")).toBeDefined();
    });
    await openReviewerSection();

    const toggleButton = screen.getByTestId("signatures-preview-toggle");
    expect(toggleButton).toBeDefined();

    // Panel should not be visible initially
    expect(screen.queryByTestId("signatures-preview-panel")).toBeNull();

    // Click to open the preview
    await act(async () => {
      fireEvent.click(toggleButton);
    });

    await waitFor(() => {
      expect(screen.getByTestId("signatures-preview-panel")).toBeDefined();
    });
  });
});

describe("Jump-to-location on inline feedback", () => {
  beforeEach(() => {
    useUserStore.setState({ ...defaultUserState });
  });

  it("renders Jump button only for inline feedback items with a range_anchor", async () => {
    renderPage();
    await openCommentsSection();

    // Wait for feedback items to load
    await waitFor(() => {
      expect(screen.getAllByTestId("jump-to-location").length).toBeGreaterThan(0);
    });

    const jumpLinks = screen.getAllByTestId("jump-to-location");
    // Only the inline item should have a Jump button
    expect(jumpLinks).toHaveLength(1);
    expect((jumpLinks[0] as HTMLAnchorElement).href).toContain("anchor=42:57");
    expect((jumpLinks[0] as HTMLAnchorElement).href).toContain("projectId=proj-preview");
  });

  it("does not render Jump button for manual feedback items", async () => {
    renderPage();
    await openCommentsSection();

    await waitFor(() => {
      // The manual feedback item text should be visible
      expect(screen.queryByText("Consider adding more detail here")).toBeDefined();
    });

    // Only one jump link (for the inline item)
    const jumpLinks = screen.queryAllByTestId("jump-to-location");
    expect(jumpLinks).toHaveLength(1);
  });
});
