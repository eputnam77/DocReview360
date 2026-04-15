import { describe, expect, it, vi } from "vitest";

import {
  assignBrowserLocation,
  downloadBrowserBlob,
  isBrowser,
  promptInBrowser,
  readLocalStorage,
  reloadCurrentPage,
  removeLocalStorage,
  resolveBrowserUrl,
  writeLocalStorage,
} from "@/lib/browser";

describe("browser helpers", () => {
  it("detects the jsdom browser environment", () => {
    expect(isBrowser()).toBe(true);
  });

  it("reads local storage through the provided storage adapter", () => {
    const storage = { getItem: vi.fn().mockReturnValue("saved-value") };

    expect(readLocalStorage("draft", storage)).toBe("saved-value");
    expect(storage.getItem).toHaveBeenCalledWith("draft");
  });

  it("writes local storage through the provided storage adapter", () => {
    const storage = { setItem: vi.fn() };

    expect(writeLocalStorage("draft", "<p>hello</p>", storage)).toBe(true);
    expect(storage.setItem).toHaveBeenCalledWith("draft", "<p>hello</p>");
  });

  it("removes local storage through the provided storage adapter", () => {
    const storage = { removeItem: vi.fn() };

    expect(removeLocalStorage("draft", storage)).toBe(true);
    expect(storage.removeItem).toHaveBeenCalledWith("draft");
  });

  it("uses the provided prompt function when available", () => {
    const prompter = vi.fn().mockReturnValue("reason text");

    expect(promptInBrowser("Why?", prompter)).toBe("reason text");
    expect(prompter).toHaveBeenCalledWith("Why?");
  });

  it("reloads the current page through the provided reloader", () => {
    const reloader = vi.fn();

    expect(reloadCurrentPage(reloader)).toBe(true);
    expect(reloader).toHaveBeenCalledTimes(1);
  });

  it("resolves a browser URL against an explicit origin", () => {
    const resolved = resolveBrowserUrl("/documenso/sig-1?from=test", "https://app.example.com");

    expect(resolved?.href).toBe("https://app.example.com/documenso/sig-1?from=test");
  });

  it("assigns browser location through the provided assigner", () => {
    const assigner = vi.fn();

    expect(assignBrowserLocation("https://example.com/sign", assigner)).toBe(true);
    expect(assigner).toHaveBeenCalledWith("https://example.com/sign");
  });

  it("downloads a blob through the provided document and URL adapters", () => {
    const click = vi.fn();
    const anchor = { href: "", download: "", click };
    const doc = {
      createElement: vi.fn().mockReturnValue(anchor),
    };
    const urlApi = {
      createObjectURL: vi.fn().mockReturnValue("blob:download"),
      revokeObjectURL: vi.fn(),
    };

    const result = downloadBrowserBlob(
      new Blob(["hello"], { type: "text/plain" }),
      "report.txt",
      doc,
      urlApi,
    );

    expect(result).toBe(true);
    expect(doc.createElement).toHaveBeenCalledWith("a");
    expect(anchor.href).toBe("blob:download");
    expect(anchor.download).toBe("report.txt");
    expect(click).toHaveBeenCalledTimes(1);
    expect(urlApi.revokeObjectURL).toHaveBeenCalledWith("blob:download");
  });
});
