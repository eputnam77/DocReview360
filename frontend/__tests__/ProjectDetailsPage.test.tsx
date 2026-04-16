import React, { act } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProjectDetailsPage from "../pages/projects/[id]";
import AuditTimeline from "@/components/AuditTimeline";
import { Disclosure, Transition } from "@headlessui/react";
import { useUserStore } from "@/state/user";

const approvalTableSpy = vi.fn();
const routerPushMock = vi.fn();

// Stable mock data — new objects on every mock call cause useEffect([dep])
// to fire infinitely (each render produces a new reference), leading to OOM.
const { stableProject, stableWorkflow, stableApprovals, stableReviewSummary } = vi.hoisted(() => ({
  stableProject: {
    id: "proj-1",
    number: "AC-01",
    type: "Test",
    title: "Test Project",
    owner: "alice",
    status: "In Progress",
    progress: 50,
    updated: "2024-01-01",
    editor: "tiptap",
    currentPhaseId: "Review",
    workflow: "workflow-1",
  },
  stableWorkflow: {
    id: "workflow-1",
    phase: "Review",
    steps: [
      { name: "Draft", status: "complete" },
      { name: "Review", status: "active" },
    ],
  },
  stableApprovals: [
    {
      id: "approval-1",
      reviewer: "alice",
      email: "alice@example.com",
      state: "pending" as const,
      dueAt: "2024-01-02",
      phaseId: "Review",
      required: true,
      role: "Approver",
      description: "Review Approval",
    },
  ],
  stableReviewSummary: { count: 0, all_complete: false },
}));

const { defaultLifecycleRecord, signFailure, authenticatedFetchMock } = vi.hoisted(() => {
  const defaultLifecycleRecord = {
    project_id: "proj-1",
    status: "draft",
    updated_at: "2024-01-01T00:00:00Z",
  };
  const signFailure = {
    enabled: false,
    payload: { id: "sig-1", url: "/sandbox/sig-1" },
  };
  const authenticatedFetchMock = vi.fn(async (url: string) => {
    if (url === "/users") {
      return { ok: true, json: async () => ["alice", "bob", "carol"] };
    }
    if (url === "/projects/proj-1/lifecycle") {
      return { ok: true, json: async () => ({ ...defaultLifecycleRecord }) };
    }
    if (url === "/projects/proj-1/assignments" || url === "/projects/proj-1/assignments/me") {
      return { ok: true, json: async () => [] };
    }
    if (url === "/projects/proj-1/feedback/progress") {
      return {
        ok: true,
        json: async () => ({ total: 0, open: 0, accepted: 0, rejected: 0, resolved: 0, addressed: 0, by_type: {} }),
      };
    }
    if (url === "/projects/proj-1/feedback") {
      return { ok: true, json: async () => ({ items: [], total: 0, skip: 0, limit: 20 }) };
    }
    if (url === "/projects/proj-1/review-summary") {
      return { ok: true, json: async () => ({ ...reviewSummaryState }) };
    }
    if (url === "/api/audit?entity_id=proj-1") {
      return { ok: true, json: async () => [] };
    }
    if (url === "/approvals/approval-1/sign") {
      if (signFailure.enabled) {
        return { ok: false, json: async () => ({ ...signFailure.payload }) };
      }
      return { ok: true, json: async () => ({ id: "approval-1", state: "approved", signedAt: "2024-01-02T10:00:00Z" }) };
    }
    return { ok: true, json: async () => [] };
  });
  return { defaultLifecycleRecord, signFailure, authenticatedFetchMock };
});

const { reviewSummaryState } = vi.hoisted(() => ({
  reviewSummaryState: {
    total_active: 0,
    invited: 0,
    reviewing: 0,
    feedback_submitted: 0,
    concurred: 0,
    non_concurred: 0,
    signed: 0,
    declined: 0,
    all_complete: false,
    all_signed: false,
    has_non_concurrence: false,
    lifecycle_step: "draft",
    feedback_total: 0,
    feedback_open: 0,
    feedback_addressed: 0,
  },
}));

const { useUserStoreMock, defaultUserState } = vi.hoisted(() => {
  const defaultState = {
    username: "alice",
    isAdmin: false,
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
    query: { id: "proj-1" },
    isReady: true,
    push: routerPushMock,
    replace: vi.fn(),
  }),
}));

vi.mock("next/link", () => ({
  default: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <a {...props}>{children}</a>
  ),
}));

vi.mock("lucide-react", () => {
  const React = require("react");
  const Icon = () => React.createElement("span");
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

vi.mock("@/components", async () => {
  const React = require("react");
  const auditTimelineModule = await vi.importActual<
    typeof import("@/components/AuditTimeline")
  >("@/components/AuditTimeline");
  return {
    ApprovalTable: (props: Record<string, unknown>) => {
      approvalTableSpy(props);
      return React.createElement("div", { "data-testid": "approval-table" });
    },
    AuditTimeline: auditTimelineModule.default,
    ProjectSummaryBar: () => React.createElement("div", null),
    KpiCards: () => React.createElement("div", null),
    PhaseAdvanceModal: () => React.createElement("div", null),
    WorkflowTimeline: () => React.createElement("div", { "data-testid": "workflow-timeline" }),
    ReviewerComments: () => React.createElement("div", { "data-testid": "reviewer-comments" }),
    UserPicker: () => React.createElement("div", { "data-testid": "user-picker" }),
    HelpTooltip: ({ children }: React.PropsWithChildren) => React.createElement("span", null, children),
    SectionErrorBoundary: ({ children }: React.PropsWithChildren) => React.createElement(React.Fragment, null, children),
  };
});

vi.mock("@/components/ui/button", () => ({
  Button: React.forwardRef<
    HTMLElement,
    React.PropsWithChildren<Record<string, unknown> & { asChild?: boolean; type?: string }>
  >(({ children, asChild = false, type = "button", ...props }, ref) => {
    if (asChild && React.isValidElement(children)) {
      return React.cloneElement(children, { ...(props as object), ref });
    }
    return React.createElement("button", { ...props, ref, type }, children);
  }),
}));

vi.mock("@/components/ui/card", () => ({
  Card: primitiveStub("div"),
  CardContent: primitiveStub("div"),
  CardHeader: primitiveStub("div"),
  CardTitle: primitiveStub("div"),
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({
    children,
    open: _open,
    onOpenChange: _onOpenChange,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => React.createElement("div", props, children),
  DialogContent: primitiveStub("div"),
  DialogHeader: primitiveStub("div"),
  DialogDescription: primitiveStub("div"),
  DialogTitle: primitiveStub("div"),
}));

vi.mock("@headlessui/react", () => {
  const React = require("react");

  const forwardRefSymbol = Symbol.for("react.forward_ref");

  const ensureSupportsRef = (element: any) => {
    const type = element?.type;
    if (!type) return false;
    if (typeof type === "string") return true;
    if (typeof type === "object" && type !== null && type.$$typeof === forwardRefSymbol) {
      return true;
    }
    return false;
  };

  const Transition = ({ show = true, as: Component = React.Fragment, children }: any) => {
    if (!show) {
      return null;
    }

    const resolved = typeof children === "function" ? children({}) : children;

    if (!React.isValidElement(resolved)) {
      return React.createElement(Component, null, resolved);
    }

    if (!ensureSupportsRef(resolved)) {
      throw new Error("Did you forget to passthrough the `ref` to the actual DOM node?");
    }

    const childRef = resolved.ref ?? React.createRef();

    return React.createElement(Component, null, React.cloneElement(resolved, { ref: childRef }));
  };

  const DisclosureContext = React.createContext<any>(null);

  const Disclosure: any = ({ children, defaultOpen = false }: any) => {
    const [open, setOpen] = React.useState(defaultOpen);
    const toggle = React.useCallback(() => setOpen((value: boolean) => !value), []);
    const contextValue = React.useMemo(() => ({ open, toggle }), [open, toggle]);
    const renderedChildren =
      typeof children === "function" ? children({ open }) : children;

    return React.createElement(
      DisclosureContext.Provider,
      { value: contextValue },
      renderedChildren,
    );
  };

  Disclosure.Button = React.forwardRef(
    ({ children, onClick, ...props }: any, ref: any) => {
      const context = React.useContext(DisclosureContext);
      if (!context) {
        throw new Error("Disclosure.Button must be used within Disclosure");
      }

      const handleClick = (event: any) => {
        context.toggle();
        onClick?.(event);
      };

      return React.createElement("button", { ...props, onClick: handleClick, ref }, children);
    },
  );

  return {
    Disclosure,
    Transition,
  };
});

vi.mock("@/lib/api", () => ({
  API: "http://example.com",
  authenticatedFetch: authenticatedFetchMock,
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
  useReviewSummary: () => ({ data: stableReviewSummary, isLoading: false, refetch: vi.fn() }),
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
  const toast = Object.assign(vi.fn(), {
    error: vi.fn(),
    success: vi.fn(),
  });
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

async function openApprovalsSection() {
  fireEvent.click(screen.getByTestId("approvals-section-toggle"));
  await waitFor(() => {
    expect(approvalTableSpy).toHaveBeenCalled();
  });
}

describe("ProjectDetailsPage", () => {
  beforeEach(() => {
    approvalTableSpy.mockClear();
    authenticatedFetchMock.mockClear();
    routerPushMock.mockReset();
    localStorage.clear();
    signFailure.enabled = false;
    signFailure.payload = { id: "sig-1", url: "/sandbox/sig-1" };
    delete stableApprovals[0].documensoSigId;
    stableReviewSummary.count = 0;
    stableReviewSummary.all_complete = false;
    defaultLifecycleRecord.status = "draft";
    reviewSummaryState.total_active = 0;
    reviewSummaryState.invited = 0;
    reviewSummaryState.reviewing = 0;
    reviewSummaryState.feedback_submitted = 0;
    reviewSummaryState.concurred = 0;
    reviewSummaryState.non_concurred = 0;
    reviewSummaryState.signed = 0;
    reviewSummaryState.declined = 0;
    reviewSummaryState.all_complete = false;
    reviewSummaryState.all_signed = false;
    reviewSummaryState.has_non_concurrence = false;
    reviewSummaryState.lifecycle_step = "draft";
    reviewSummaryState.feedback_total = 0;
    reviewSummaryState.feedback_open = 0;
    reviewSummaryState.feedback_addressed = 0;
    useUserStore.setState({ ...defaultUserState });
  });

  it("renders without crashing and forwards currentUser to ApprovalTable", async () => {
    const { container } = renderPage();

    await openApprovalsSection();

    expect(container.innerHTML).toContain("data-testid=\"approval-table\"");
    const currentUsers = approvalTableSpy.mock.calls.map(([props]: [Record<string, unknown>]) => props.currentUser);
    expect(currentUsers).toContain("alice");
  });

  it("renders approvals above reviewer sign-off and keeps those sections collapsed by default", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("approvals-section-toggle")).toBeDefined();
    });

    const approvalsToggle = screen.getByTestId("approvals-section-toggle");
    const reviewerToggle = screen.getByTestId("reviewer-signoff-section-toggle");
    const commentsToggle = screen.getByTestId("comments-section-toggle");

    expect(
      approvalsToggle.compareDocumentPosition(reviewerToggle) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      reviewerToggle.compareDocumentPosition(commentsToggle) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.queryByTestId("approval-table")).toBeNull();
  });

  it("routes approval signing through the local documenso page when the backend returns an unsupported local path", async () => {
    signFailure.enabled = true;
    renderPage();

    await openApprovalsSection();

    const latestProps = approvalTableSpy.mock.calls.at(-1)?.[0] as { handlers: { onSign: (id: string) => Promise<void> } };
    await act(async () => {
      await latestProps.handlers.onSign("approval-1");
    });

    expect(routerPushMock).toHaveBeenCalledWith(
      "/documenso/sig-1?return=%2Fprojects%2Fproj-1%23approvals&approval=approval-1",
    );
  });

  it("does not issue a duplicate approval update when local signature completion is restored from storage", async () => {
    stableApprovals[0].documensoSigId = "sig-1";
    localStorage.setItem("approval-approval-1", "2024-01-02T10:00:00Z");

    renderPage();

    await waitFor(() => {
      expect(authenticatedFetchMock).toHaveBeenCalled();
    });

    expect(
      authenticatedFetchMock.mock.calls.some(
        ([url, options]: [string, RequestInit | undefined]) =>
          url === "/approvals/approval-1" && options?.method === "PUT",
      ),
    ).toBe(false);
  });

  it("shows the reviewed lifecycle state when reviewer sign-off is complete", async () => {
    stableReviewSummary.count = 1;
    stableReviewSummary.all_complete = true;
    reviewSummaryState.total_active = 1;
    reviewSummaryState.concurred = 1;
    reviewSummaryState.all_complete = true;
    reviewSummaryState.lifecycle_step = "reviewed";
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("project-lifecycle-reviewed").className).toContain("ring-1");
    });
    expect(screen.getByTestId("project-lifecycle-in_review").className).toContain("bg-green-100");
    expect(
      screen.getByText("Reviewer sign-off is complete. Advance the formal project lifecycle when you are ready."),
    ).toBeDefined();
  });

  it("allows expanding the audit history panel with the real Transition", () => {
    const HistoryPanel = () => (
      <Disclosure defaultOpen>
        {({ open }) => (
          <>
            <Disclosure.Button>Audit History</Disclosure.Button>
            <Transition show={open}>
              <AuditTimeline events={[]} />
            </Transition>
          </>
        )}
      </Disclosure>
    );

    const { unmount } = render(<HistoryPanel />);
    const toggle = screen.getByRole("button", { name: /audit history/i });

    fireEvent.click(toggle);

    expect(() => fireEvent.click(toggle)).not.toThrow();

    unmount();
  });
});
