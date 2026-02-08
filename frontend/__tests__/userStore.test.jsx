import React, { act } from "react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { createRoot } from "react-dom/client";
import { useUserStore } from "@/state/user";
import LoginPage from "@/pages/login";
import { authenticatedFetch } from "@/lib/api";
vi.mock("@/lib/api", () => ({
    API: "http://test",
    authenticatedFetch: vi.fn(),
}));
vi.mock("react-hot-toast", () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));
const pushMock = vi.fn();
vi.mock("next/router", () => ({
    useRouter: () => ({
        push: pushMock,
    }),
}));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mockAuthenticatedFetch = vi.mocked(authenticatedFetch);
const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));
const originalRefresh = useUserStore.getState().refresh;
const clearSessionCookies = () => {
    document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
};
describe("user store", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        clearSessionCookies();
        useUserStore.setState({
            isAdmin: false,
            isAuditor: false,
            username: "",
            theme: "system",
            initialized: false,
            refresh: originalRefresh,
        });
    });
    afterEach(() => {
        clearSessionCookies();
        useUserStore.setState({
            isAdmin: false,
            isAuditor: false,
            username: "",
            theme: "system",
            initialized: false,
            refresh: originalRefresh,
        });
    });
    it("skips the session fetch when no access token is present", async () => {
        await useUserStore.getState().initialize();
        expect(mockAuthenticatedFetch).not.toHaveBeenCalled();
        const state = useUserStore.getState();
        expect(state.username).toBe("");
        expect(state.isAdmin).toBe(false);
        expect(state.isAuditor).toBe(false);
        expect(state.initialized).toBe(true);
    });
    it("returns early when /users/me responds with 401", async () => {
        document.cookie = "access_token=test; path=/";
        mockAuthenticatedFetch.mockResolvedValueOnce(new Response(null, { status: 401 }));
        await useUserStore.getState().initialize();
        expect(mockAuthenticatedFetch).toHaveBeenCalledTimes(1);
        expect(mockAuthenticatedFetch).toHaveBeenCalledWith("/users/me");
        const state = useUserStore.getState();
        expect(state.username).toBe("");
        expect(state.isAdmin).toBe(false);
        expect(state.isAuditor).toBe(false);
        expect(state.initialized).toBe(true);
    });
    it("hydrates the user and profile after a successful session fetch", async () => {
        document.cookie = "access_token=test; path=/";
        const sessionResponse = {
            ok: true,
            status: 200,
            json: vi.fn().mockResolvedValue({
                username: "alice",
                roles: ["admin", "auditor"],
            }),
        };
        const profileResponse = {
            ok: true,
            status: 200,
            json: vi.fn().mockResolvedValue({
                preferences: { theme: "dark" },
            }),
        };
        mockAuthenticatedFetch
            .mockResolvedValueOnce(sessionResponse)
            .mockResolvedValueOnce(profileResponse);
        await useUserStore.getState().initialize();
        expect(mockAuthenticatedFetch).toHaveBeenNthCalledWith(1, "/users/me");
        expect(mockAuthenticatedFetch).toHaveBeenNthCalledWith(2, "/profile");
        const state = useUserStore.getState();
        expect(state.username).toBe("alice");
        expect(state.isAdmin).toBe(true);
        expect(state.isAuditor).toBe(true);
        expect(state.theme).toBe("dark");
        expect(state.initialized).toBe(true);
    });
});
describe("login page", () => {
    const originalFetch = global.fetch;
    beforeEach(() => {
        pushMock.mockReset();
        vi.clearAllMocks();
        clearSessionCookies();
        useUserStore.setState({
            isAdmin: false,
            isAuditor: false,
            username: "",
            theme: "system",
            initialized: false,
            refresh: originalRefresh,
        });
    });
    afterEach(() => {
        if (originalFetch) {
            global.fetch = originalFetch;
        }
        useUserStore.setState({ refresh: originalRefresh });
        clearSessionCookies();
    });
    it("refreshes the user store after a successful login", async () => {
        const refreshMock = vi.fn().mockResolvedValue(undefined);
        useUserStore.setState({ refresh: refreshMock });
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue({}),
        });
        global.fetch = fetchMock;
        const container = document.createElement("div");
        document.body.appendChild(container);
        const root = createRoot(container);
        await act(async () => {
            root.render(<LoginPage />);
        });
        const usernameInput = container.querySelector("input#username");
        const passwordInput = container.querySelector("input#password");
        const form = container.querySelector("form");
        await act(async () => {
            usernameInput.value = "alice";
            usernameInput.dispatchEvent(new Event("input", { bubbles: true }));
            passwordInput.value = "password";
            passwordInput.dispatchEvent(new Event("input", { bubbles: true }));
        });
        await act(async () => {
            form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
            await flushPromises();
        });
        await act(async () => {
            await flushPromises();
        });
        expect(fetchMock).toHaveBeenCalledWith("http://test/token", expect.anything());
        expect(refreshMock).toHaveBeenCalledTimes(1);
        expect(pushMock).toHaveBeenCalledWith("/projects");
        expect(refreshMock.mock.invocationCallOrder[0]).toBeLessThan(pushMock.mock.invocationCallOrder[0]);
        await act(async () => {
            root.unmount();
        });
        container.remove();
    });
});
