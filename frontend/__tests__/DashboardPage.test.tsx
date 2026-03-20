import React from "react";
import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MainDashboardPage from "../pages/dashboard";

const { fetchMock } = vi.hoisted(() => ({ fetchMock: vi.fn() }));

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

const { useUserStoreMock } = vi.hoisted(() => {
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
  hook.reset = () => {
    Object.assign(store, defaultState);
  };
  return { useUserStoreMock: hook };
});

vi.mock("@/state/user", () => ({
  useUserStore: useUserStoreMock,
}));

vi.mock("@/lib/api", () => ({
  authenticatedFetch: fetchMock,
}));

vi.mock("@/state/visibility", () => ({
  useDashboardVisibility: () => ({
    vis: { stats: true, status: true, activity: true, logs: true },
  }),
}));

vi.mock("@/components", () => ({
  ChatBot: () => <div data-testid="chatbot" />,
}));

vi.mock("@/components/ui/card", () => {
  const React = require("react");
  const primitive = (tag: keyof React.JSX.IntrinsicElements) =>
    ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) =>
      React.createElement(tag, props, children);
  return {
    Card: primitive("div"),
    CardContent: primitive("div"),
    CardHeader: primitive("div"),
    CardTitle: primitive("div"),
  };
});

vi.mock("@/components/ui/tabs", () => {
  const React = require("react");
  const primitive = (tag: keyof React.JSX.IntrinsicElements) =>
    ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) =>
      React.createElement(tag, props, children);
  const Tabs = primitive("div");
  return {
    Tabs,
    TabsList: primitive("div"),
    TabsTrigger: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <button {...props}>{children}</button>
    ),
    TabsContent: primitive("div"),
  };
});

vi.mock("lucide-react", () => {
  const React = require("react");
  const Icon = ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <span {...props}>{children}</span>
  );
  return {
    LayoutDashboard: Icon,
    FolderOpen: Icon,
    Users2: Icon,
    CheckCircle2: Icon,
    Clock: Icon,
    BarChart2: Icon,
  };
});

const renderWithClient = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

vi.mock("recharts", () => {
  const React = require("react");
  const container = ({ children }: React.PropsWithChildren) => <div>{children}</div>;
  const Leaf = () => <div />;
  return {
    ResponsiveContainer: container,
    PieChart: container,
    Pie: container,
    Cell: Leaf,
    LineChart: container,
    Line: Leaf,
    XAxis: Leaf,
    YAxis: Leaf,
    Tooltip: Leaf,
  };
});

describe("DashboardPage", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    useUserStoreMock.reset();
  });

  it("renders dashboard metrics from API data", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue([
        { id: "1", status: "In Progress", user: "alice", updated: "2024-01-02T10:00:00Z" },
        { id: "2", status: "Complete", assignees: ["alice"], updated: "2024-01-03T08:00:00Z" },
        { id: "3", status: "Overdue", user: "bob", updated: "2024-01-03T09:00:00Z" },
      ]),
    });
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue([
        { timestamp: "2024-01-03T12:00:00Z", action: "Review completed", metadata: { project: "AC-1" } },
        { timestamp: "2024-01-02T09:15:00Z", action: "Project created", metadata: { project: "AC-2" } },
      ]),
    });

    renderWithClient(<MainDashboardPage />);

    await screen.findByText("Review completed");

    const assignedLabel = screen.getByText("Assigned to Me");
    const assignedValue = assignedLabel.parentElement?.querySelector("p:first-child");
    expect(assignedValue?.textContent).toBe("2");

    const inProgressValue = screen.getByText("In Progress").parentElement?.querySelector("p:first-child");
    const completedValue = screen.getByText("Completed").parentElement?.querySelector("p:first-child");
    const overdueValue = screen.getByText("Overdue").parentElement?.querySelector("p:first-child");

    expect(inProgressValue?.textContent).toBe("1");
    expect(completedValue?.textContent).toBe("1");
    expect(overdueValue?.textContent).toBe("1");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/projects");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/logs?limit=20");

    expect(screen.getByText("Project created")).toBeTruthy();
    expect(screen.getByText("Review completed")).toBeTruthy();

    const feed = screen.getByText("Project created").closest("ul");
    expect(feed).not.toBeNull();
    if (feed) {
      expect(within(feed).getAllByRole("listitem")).toHaveLength(2);
    }
  });
  it("counts reviewer-visible projects as assigned work for the active reviewer", async () => {
    useUserStoreMock.setState({ username: "bob" });
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue([
        { id: "review-1", status: "In Progress", reviewers: ["bob"], updated: "2024-01-03T08:00:00Z" },
      ]),
    });
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue([]),
    });

    renderWithClient(<MainDashboardPage />);

    await screen.findByText("Assigned to Me");

    const assignedValue = screen.getByText("Assigned to Me").parentElement?.querySelector("p:first-child");
    expect(assignedValue?.textContent).toBe("1");
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/projects");
  });
});
