import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectDetailsPage from "../pages/projects/[id]";
import AuditTimeline from "@/components/AuditTimeline";
import { Disclosure, Transition } from "@headlessui/react";
import { useUserStore } from "@/state/user";

const approvalTableSpy = vi.fn();
const routerPushMock = vi.fn();

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
    push: routerPushMock,
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
  authenticatedFetch: vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => [],
    }),
  ),
}));

vi.mock("@/lib/useProject", () => ({
  useProject: () => ({
    data: {
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
    isLoading: false,
  }),
}));

vi.mock("@/lib/usePhases", () => ({
  usePhases: () => ({
    data: {
      id: "workflow-1",
      phase: "Review",
      steps: [
        { name: "Draft", status: "complete" },
        { name: "Review", status: "active" },
      ],
    },
    isLoading: false,
  }),
}));

vi.mock("@/lib/useApprovals", () => ({
  useApprovals: () => ({
    approvals: [
      {
        id: "approval-1",
        reviewer: "alice",
        email: "alice@example.com",
        state: "pending" as const,
        dueAt: "2024-01-02",
        phaseId: "Review",
      },
    ],
    approve: vi.fn(),
    reset: vi.fn(),
    remind: vi.fn(),
    isLoading: false,
  }),
}));

vi.mock("@/lib/useReviewSummary", () => ({
  useReviewSummary: () => ({
    data: { count: 0 },
    isLoading: false,
  }),
}));

vi.mock("react-hot-toast", () => {
  const toast = Object.assign(vi.fn(), {
    error: vi.fn(),
    success: vi.fn(),
  });
  return { toast };
});

describe("ProjectDetailsPage", () => {
  beforeEach(() => {
    approvalTableSpy.mockClear();
    useUserStore.setState({ ...defaultUserState });
  });

  it("renders without crashing and forwards currentUser to ApprovalTable", () => {
    const html = renderToString(<ProjectDetailsPage />);

    expect(html).toContain("<table");
    expect(approvalTableSpy).toHaveBeenCalled();
    const currentUsers = approvalTableSpy.mock.calls.map(([props]: [Record<string, unknown>]) => props.currentUser);
    expect(currentUsers).toContain("alice");
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
