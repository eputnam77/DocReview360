import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectList from "../pages/projects";
const { fetchSpy } = vi.hoisted(() => ({ fetchSpy: vi.fn() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
function primitiveStub(tag) {
    return ({ children, ...props }) => React.createElement(tag, props, children);
}
const { useUserStoreMock } = vi.hoisted(() => {
    const defaultState = {
        username: "alice",
        isAdmin: false,
        isAuditor: false,
    };
    const store = { ...defaultState };
    const hook = (selector) => selector(store);
    hook.setState = (partial) => {
        Object.assign(store, partial);
    };
    hook.getState = () => store;
    hook.reset = () => {
        Object.assign(store, defaultState);
    };
    return { useUserStoreMock: hook };
});
vi.mock("@/state/user", () => ({
    useUserStore: useUserStoreMock,
}));
vi.mock("@/lib/api", () => ({
    API: "http://example.com",
    authenticatedFetch: fetchSpy,
}));
vi.mock("next/link", () => ({
    default: ({ children, ...props }) => (<a {...props}>{children}</a>),
}));
vi.mock("lucide-react", () => {
    const React = require("react");
    const Icon = () => React.createElement("span");
    return {
        Users2: Icon,
        CheckCircle2: Icon,
        Clock: Icon,
        BarChart2: Icon,
    };
});
vi.mock("@/components/ui/button", () => {
    const React = require("react");
    const Button = ({ children, asChild, ...props }) => {
        if (asChild && React.isValidElement(children)) {
            return React.cloneElement(children, props);
        }
        return React.createElement("button", props, children);
    };
    return { Button };
});
vi.mock("@/components/ui/card", () => ({
    Card: primitiveStub("div"),
    CardContent: primitiveStub("div"),
}));
vi.mock("@/components/ui/table", () => ({
    Table: primitiveStub("table"),
    TableHeader: primitiveStub("thead"),
    TableBody: primitiveStub("tbody"),
    TableRow: primitiveStub("tr"),
    TableHead: primitiveStub("th"),
    TableCell: primitiveStub("td"),
}));
describe("ProjectList API selection", () => {
    beforeEach(() => {
        fetchSpy.mockReset();
        useUserStoreMock.reset();
    });
    it("requests all projects for administrators", async () => {
        fetchSpy.mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue([]),
        });
        useUserStoreMock.setState({ username: "admin", isAdmin: true });
        const container = document.createElement("div");
        const root = createRoot(container);
        await act(async () => {
            root.render(<ProjectList />);
        });
        await act(async () => {
            await Promise.resolve();
        });
        expect(fetchSpy).toHaveBeenCalledWith("/projects");
        await act(async () => {
            root.unmount();
        });
    });
    it("requests user-specific projects for standard users", async () => {
        fetchSpy.mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue([]),
        });
        useUserStoreMock.setState({ username: "bob", isAdmin: false });
        const container = document.createElement("div");
        const root = createRoot(container);
        await act(async () => {
            root.render(<ProjectList />);
        });
        await act(async () => {
            await Promise.resolve();
        });
        expect(fetchSpy).toHaveBeenCalledWith("/projects?user=bob");
        await act(async () => {
            root.unmount();
        });
    });
});
