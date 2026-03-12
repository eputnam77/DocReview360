/**
 * Tests for LocaleSwitcher component — locale switching behavior.
 */
import React from "react";
import { render, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

// Mock the useTranslation hook so the component doesn't need QueryClientProvider.
const mockSetLocale = vi.fn();
let mockLocale = "en";

vi.mock("@/lib/useTranslation", () => ({
  useTranslation: () => ({
    locale: mockLocale,
    setLocale: mockSetLocale,
    t: (key: string, fallback?: string) => fallback ?? key,
    isLoading: false,
  }),
}));

import LocaleSwitcher from "@/components/LocaleSwitcher";

beforeEach(() => {
  mockSetLocale.mockReset();
  mockLocale = "en";
});

describe("LocaleSwitcher", () => {
  it("renders a select with all four supported locales", () => {
    const { getByRole, getAllByRole } = render(<LocaleSwitcher />);
    const select = getByRole("combobox", { name: /select language/i });
    expect(select).toBeTruthy();
    const options = getAllByRole("option");
    const codes = options.map((o) => (o as HTMLOptionElement).value);
    expect(codes).toContain("en");
    expect(codes).toContain("es");
    expect(codes).toContain("fr");
    expect(codes).toContain("de");
    expect(options).toHaveLength(4);
  });

  it("shows the current locale as the selected value", () => {
    mockLocale = "de";
    const { getByRole } = render(<LocaleSwitcher />);
    const select = getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("de");
  });

  it("calls setLocale with the newly selected locale on change", () => {
    const { getByRole } = render(<LocaleSwitcher />);
    const select = getByRole("combobox");
    fireEvent.change(select, { target: { value: "fr" } });
    expect(mockSetLocale).toHaveBeenCalledOnce();
    expect(mockSetLocale).toHaveBeenCalledWith("fr");
  });

  it("calls setLocale when switching to each supported locale", () => {
    const { getByRole } = render(<LocaleSwitcher />);
    const select = getByRole("combobox");
    for (const code of ["es", "fr", "de", "en"]) {
      fireEvent.change(select, { target: { value: code } });
      expect(mockSetLocale).toHaveBeenLastCalledWith(code);
    }
    expect(mockSetLocale).toHaveBeenCalledTimes(4);
  });

  it("has an accessible aria-label for screen readers", () => {
    const { getByRole } = render(<LocaleSwitcher />);
    const select = getByRole("combobox", { name: /select language/i });
    expect(select).toBeTruthy();
  });
});
