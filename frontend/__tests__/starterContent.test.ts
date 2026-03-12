import { describe, expect, it, vi } from "vitest";
import { resolveStarterContent } from "@/lib/starterContent";

// Identity sanitizer for tests — proves the raw HTML flows through.
const identity = (html: string) => html;

describe("resolveStarterContent — success path", () => {
  it("returns starter HTML when endpoint responds 200 with content", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ content: "<h1>SOP Starter</h1>" }), { status: 200 }),
    );

    const result = await resolveStarterContent("SOP", fetchStarter, identity, []);

    expect(result).toEqual({ source: "starter", html: "<h1>SOP Starter</h1>" });
    expect(fetchStarter).toHaveBeenCalledOnce();
    expect(fetchStarter).toHaveBeenCalledWith("SOP");
  });

  it("passes the HTML through the sanitize function", async () => {
    const sanitize = vi.fn((html: string) => html.replace(/<script[^>]*>.*?<\/script>/gi, ""));
    const fetchStarter = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ content: "<p>Safe</p><script>evil()</script>" }), {
        status: 200,
      }),
    );

    const result = await resolveStarterContent("SOP", fetchStarter, sanitize, []);

    expect(result).toEqual({ source: "starter", html: "<p>Safe</p>" });
    expect(sanitize).toHaveBeenCalledWith("<p>Safe</p><script>evil()</script>");
  });
});

describe("resolveStarterContent — 404 / empty fallback", () => {
  it("falls back to a matching default template on 404", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    const templates = [
      { id: "sop-default", docType: "SOP", default: true },
      { id: "other-tpl", docType: "WI" },
    ];

    const result = await resolveStarterContent("SOP", fetchStarter, identity, templates);

    expect(result).toEqual({ source: "template", templateId: "sop-default" });
  });

  it("falls back to a non-default template when no default matches", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    const templates = [{ id: "sop-tpl", docType: "SOP" }];

    const result = await resolveStarterContent("SOP", fetchStarter, identity, templates);

    expect(result).toEqual({ source: "template", templateId: "sop-tpl" });
  });

  it("prefers the default template over a non-default when both match", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    const templates = [
      { id: "sop-plain", docType: "SOP" },
      { id: "sop-preferred", docType: "SOP", isDefault: true },
    ];

    const result = await resolveStarterContent("SOP", fetchStarter, identity, templates);

    expect(result).toEqual({ source: "template", templateId: "sop-preferred" });
  });

  it("returns none when 404 and no template matches the doc-type", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    const templates = [{ id: "wi-tpl", docType: "WI" }];

    const result = await resolveStarterContent("SOP", fetchStarter, identity, templates);

    expect(result).toEqual({ source: "none" });
  });

  it("returns none when 404 and templates list is empty", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));

    const result = await resolveStarterContent("SOP", fetchStarter, identity, []);

    expect(result).toEqual({ source: "none" });
  });

  it("returns none when 200 but content is blank whitespace", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ content: "   \n  " }), { status: 200 }),
    );

    const result = await resolveStarterContent("SOP", fetchStarter, identity, []);

    expect(result).toEqual({ source: "none" });
  });

  it("returns none when 200 but sanitizer strips content to empty string", async () => {
    const stripAll = () => "";
    const fetchStarter = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ content: "<p>anything</p>" }), { status: 200 }),
    );

    const result = await resolveStarterContent("SOP", fetchStarter, stripAll, []);

    expect(result).toEqual({ source: "none" });
  });
});

describe("resolveStarterContent — network error fallback", () => {
  it("falls back to template on fetch network error", async () => {
    const fetchStarter = vi.fn().mockRejectedValue(new TypeError("Network failed"));
    const templates = [{ id: "sop-tpl", docType: "SOP" }];

    const result = await resolveStarterContent("SOP", fetchStarter, identity, templates);

    expect(result).toEqual({ source: "template", templateId: "sop-tpl" });
  });

  it("returns none when network error and no templates", async () => {
    const fetchStarter = vi.fn().mockRejectedValue(new TypeError("Network failed"));

    const result = await resolveStarterContent("SOP", fetchStarter, identity, []);

    expect(result).toEqual({ source: "none" });
  });
});

describe("resolveStarterContent — case-insensitive doc-type matching", () => {
  it("matches template when doc-type case differs", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    const templates = [{ id: "sop-tpl", docType: "sop" }];

    const result = await resolveStarterContent("SOP", fetchStarter, identity, templates);

    expect(result).toEqual({ source: "template", templateId: "sop-tpl" });
  });

  it("matches template when stored as doc_type (underscore variant)", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    const templates = [{ id: "sop-tpl", doc_type: "SOP" }];

    const result = await resolveStarterContent("SOP", fetchStarter, identity, templates);

    expect(result).toEqual({ source: "template", templateId: "sop-tpl" });
  });

  it("falls back to template.name when template.id is absent", async () => {
    const fetchStarter = vi.fn().mockResolvedValue(new Response(null, { status: 404 }));
    const templates = [{ name: "sop-by-name", type: "SOP" }];

    const result = await resolveStarterContent("SOP", fetchStarter, identity, templates);

    expect(result).toEqual({ source: "template", templateId: "sop-by-name" });
  });
});
