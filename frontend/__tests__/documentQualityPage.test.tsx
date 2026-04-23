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

  it("renders the standalone FSV iframe without DocReview360 wrapper controls", () => {
    vi.stubEnv("NEXT_PUBLIC_FSV_FRONTEND_URL", "https://fsv.example.com/embed");

    render(<DocumentQualityPage />);

    const frame = screen.getByTitle("Federal Style Validator");
    expect(frame.getAttribute("src")).toBe("https://fsv.example.com/embed");
    expect(screen.queryByText("Powered by Federal Style Validator")).toBeNull();
    expect(screen.queryByRole("link", { name: /open in new tab/i })).toBeNull();
  });

  it("shows a minimal configuration fallback when the standalone frontend URL is missing", () => {
    vi.stubEnv("NEXT_PUBLIC_FSV_FRONTEND_URL", "");

    render(<DocumentQualityPage />);

    expect(screen.getByRole("heading", { name: "FSV frontend is not configured" })).toBeDefined();
    expect(screen.getByText(/NEXT_PUBLIC_FSV_FRONTEND_URL/)).toBeDefined();
    expect(screen.queryByTitle("Federal Style Validator")).toBeNull();
  });
});
