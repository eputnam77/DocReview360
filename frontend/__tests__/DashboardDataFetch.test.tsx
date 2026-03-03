import React from "react";
import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import UserDashboardPage from "../pages/dashboard/user";
import ManagerDashboardPage from "../pages/dashboard/manager";

const { fetchMock } = vi.hoisted(() => ({ fetchMock: vi.fn() }));

const { useUserStoreMock } = vi.hoisted(() => {
  const defaultState = { username: "alice" };
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

vi.mock("@/lib/api", () => ({
  authenticatedFetch: fetchMock,
}));

vi.mock("@/state/user", () => ({
  useUserStore: useUserStoreMock,
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

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <button {...props}>{children}</button>
  ),
}));

vi.mock("@/components/ui/tabs", () => {
  const React = require("react");
  const primitive = (tag: keyof React.JSX.IntrinsicElements) =>
    ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) =>
      React.createElement(tag, props, children);
  return {
    Tabs: primitive("div"),
    TabsList: primitive("div"),
    TabsTrigger: primitive("button"),
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
    Clock: Icon,
    CheckCircle2: Icon,
    Users2: Icon,
    FileText: Icon,
    BarChart2: Icon,
    MessageCircle: Icon,
    BookOpen: Icon,
    CalendarClock: Icon,
    AlertTriangle: Icon,
    ThumbsUp: Icon,
    ShieldCheck: Icon,
    PieChart: Icon,
    TrendingUp: Icon,
    UserCheck: Icon,
  };
});

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
    BarChart: container,
    Bar: Leaf,
  };
});

const renderWithClient = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
};

describe("Dashboard data fetches", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    useUserStoreMock.reset();
  });

  it("requests user dashboard data with the acting username", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue([]),
    });

    renderWithClient(<UserDashboardPage />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/dashboard/user", {
        headers: { "X-User": "alice" },
      });
    });
  });

  it("uses authenticated fetches for manager dashboard widgets", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: vi.fn().mockResolvedValue({ projects: [], workload: {} }),
    });

    renderWithClient(<ManagerDashboardPage />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/dashboard/manager");
    });
  });
});
