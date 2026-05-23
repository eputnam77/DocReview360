import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import DocumentQualityPage, {
  normalizeExternalUrl,
  resolveFsvFrontendUrl,
} from "../pages/tools/document-quality";

describe("document-quality page helpers", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("normalizes supported external URLs and trims the trailing slash", () => {
    expect(normalizeExternalUrl(" https://fsv.example.com/app/ ")).toBe("https://fsv.example.com/app");
  });

  it("rejects empty, invalid, and non-http URLs", () => {
    expect(normalizeExternalUrl("")).toBeNull();
    expect(normalizeExternalUrl("not a url")).toBeNull();
    expect(normalizeExternalUrl("ftp://fsv.example.com")).toBeNull();
  });

  it("reads the FSV frontend URL from NEXT_PUBLIC_FSV_FRONTEND_URL", () => {
    vi.stubEnv("NEXT_PUBLIC_FSV_FRONTEND_URL", "https://fsv.example.com/embed/");
    expect(resolveFsvFrontendUrl()).toBe("https://fsv.example.com/embed");
  });
});

describe("DocumentQualityPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
  });

  it("renders the configured FSV iframe with a built-in fallback action", () => {
    vi.stubEnv("NEXT_PUBLIC_FSV_FRONTEND_URL", "https://fsv.example.com/embed");

    render(<DocumentQualityPage />);

    const frame = screen.getByTitle("Federal Style Validator");
    expect(frame.getAttribute("src")).toBe("https://fsv.example.com/embed");
    expect(screen.getByRole("link", { name: "Open standalone" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Use built-in validator" })).toBeDefined();
  });

  it("shows the built-in validator when the standalone frontend URL is missing", () => {
    vi.stubEnv("NEXT_PUBLIC_FSV_FRONTEND_URL", "");

    render(<DocumentQualityPage />);

    expect(screen.getByRole("heading", { name: "Federal Style Validator" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Run validation" })).toBeDefined();
    expect(screen.queryByTitle("Federal Style Validator")).toBeNull();
  });
});
