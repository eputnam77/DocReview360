import React from "react";
import { render, cleanup } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it } from "vitest";
import axe from "axe-core";

import PrivacyPage from "../pages/privacy";
import SignupPage from "../pages/signup";
import TermsPage from "../pages/terms";

async function expectNoAxeViolations(ui: React.ReactElement) {
  const { container } = render(ui);
  const results = await axe.run(container);
  expect(results.violations).toHaveLength(0);
}

beforeAll(() => {
  Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
    value: () => null,
  });
});

afterEach(() => {
  cleanup();
});

describe("page-level accessibility checks (Task 3)", () => {
  it("signup page has no basic axe violations", async () => {
    await expectNoAxeViolations(<SignupPage />);
  });

  it("terms page has no basic axe violations", async () => {
    await expectNoAxeViolations(<TermsPage />);
  });

  it("privacy page has no basic axe violations", async () => {
    await expectNoAxeViolations(<PrivacyPage />);
  });
});
