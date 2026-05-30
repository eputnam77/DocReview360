import { describe, expect, it } from "vitest";

import sanitizeHtml from "@/utils/sanitize";

describe("sanitizeHtml", () => {
  it("drops executable elements and their contents", () => {
    const result = sanitizeHtml('<p>Safe</p><script>alert("x")</script><iframe src="https://example.com"></iframe>');

    expect(result).toBe("<p>Safe</p>");
  });

  it("removes event handlers and unsafe URL attributes while preserving safe markup", () => {
    const result = sanitizeHtml(
      '<h2 onclick="steal()">Title</h2><a href="javascript:alert(1)" target="_blank">bad</a><a href="/docs/1" target="_blank">good</a>',
    );

    expect(result).toBe('<h2>Title</h2><a target="_blank" rel="noopener noreferrer">bad</a><a href="/docs/1" target="_blank" rel="noopener noreferrer">good</a>');
  });

  it("keeps table structure and strips style attributes", () => {
    const result = sanitizeHtml('<table style="background:url(javascript:evil)"><tbody><tr><th scope="col">Name</th><td colspan="2">Value</td></tr></tbody></table>');

    expect(result).toBe('<table><tbody><tr><th scope="col">Name</th><td colspan="2">Value</td></tr></tbody></table>');
  });
});
