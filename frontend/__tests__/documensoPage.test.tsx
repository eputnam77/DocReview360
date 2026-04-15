import React, { act } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import DocumensoSign from "../pages/documenso/[sig]";

const { authenticatedFetchMock, routerPushMock, routerState } = vi.hoisted(() => ({
  authenticatedFetchMock: vi.fn(),
  routerPushMock: vi.fn(),
  routerState: {
    query: {
      sig: "sig-1",
      approval: "approval-1",
      return: "/projects/proj-1#approvals",
    },
    isReady: true,
    push: vi.fn(),
  },
}));

routerState.push = routerPushMock;

vi.mock("@/lib/api", () => ({
  authenticatedFetch: authenticatedFetchMock,
}));

vi.mock("next/router", () => ({
  useRouter: () => routerState,
}));

vi.mock("lucide-react", () => ({
  ShieldCheck: (props: Record<string, unknown>) => <span {...props} />,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    ...props
  }: React.PropsWithChildren<React.ButtonHTMLAttributes<HTMLButtonElement>>) => (
    <button type="button" {...props}>
      {children}
    </button>
  ),
}));

vi.mock("@/components/ui/card", () => ({
  Card: ({ children, ...props }: React.PropsWithChildren<React.HTMLAttributes<HTMLDivElement>>) => (
    <div {...props}>{children}</div>
  ),
  CardContent: ({ children, ...props }: React.PropsWithChildren<React.HTMLAttributes<HTMLDivElement>>) => (
    <div {...props}>{children}</div>
  ),
  CardHeader: ({ children, ...props }: React.PropsWithChildren<React.HTMLAttributes<HTMLDivElement>>) => (
    <div {...props}>{children}</div>
  ),
  CardTitle: ({ children, ...props }: React.PropsWithChildren<React.HTMLAttributes<HTMLHeadingElement>>) => (
    <h1 {...props}>{children}</h1>
  ),
}));

describe("DocumensoSign", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    authenticatedFetchMock.mockReset();
    routerPushMock.mockReset();
    localStorage.clear();
    authenticatedFetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: vi.fn().mockResolvedValue({}),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("completes the signature without issuing a second approval update request", async () => {
    render(<DocumensoSign />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Sign & Approve" }));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(authenticatedFetchMock).toHaveBeenCalledTimes(1);
    expect(authenticatedFetchMock).toHaveBeenCalledWith("/sign/sig-1/complete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });
    expect(
      authenticatedFetchMock.mock.calls.some(([url]: [string]) => url === "/approvals/approval-1"),
    ).toBe(false);

    expect(localStorage.getItem("approval-approval-1")).toMatch(/T/);
    expect(screen.getByText(/Document signed and approved/i)).toBeDefined();

    await act(async () => {
      vi.runOnlyPendingTimers();
    });

    expect(routerPushMock).toHaveBeenCalledWith("/projects/proj-1#approvals");
  });
});
