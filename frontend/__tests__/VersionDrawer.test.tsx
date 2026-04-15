import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VersionDrawer } from "@/components/project/VersionDrawer";

describe("VersionDrawer", () => {
  const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  const versions = [
    {
      id: "version-1",
      action: "Saved draft",
      timestamp: "2026-04-15T12:00:00Z",
      author: "alice",
    },
  ];

  afterEach(() => {
    consoleErrorSpy.mockClear();
  });

  it("renders the accessible dialog title and version details when open", () => {
    render(<VersionDrawer open onClose={vi.fn()} versions={versions} />);

    expect(
      screen.getByRole("dialog", { name: "Document Versions" }),
    ).toBeTruthy();
    expect(
      screen.getByText("Review saved document versions and the author for each change."),
    ).toBeTruthy();
    expect(screen.getByText("Saved draft")).toBeTruthy();
    expect(screen.getByText(/alice/)).toBeTruthy();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it("closes exactly once when Escape is pressed", () => {
    const onClose = vi.fn();
    render(<VersionDrawer open onClose={onClose} versions={versions} />);

    fireEvent.keyDown(
      screen.getByRole("dialog", { name: "Document Versions" }),
      { key: "Escape" },
    );

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });
});
