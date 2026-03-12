import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => {
  const fetchMock = vi.fn();
  return {
    API: "http://example.com",
    authenticatedFetch: fetchMock,
  };
});

import { authenticatedFetch } from "@/lib/api";
import { createTiptapApi } from "@/pages/editors/tiptap";
import { createWordTemplateApi } from "@/pages/editors/word";
import { createTemplateConfigApi } from "@/pages/configuration/templates";

const mockAuthenticatedFetch = vi.mocked(authenticatedFetch);

beforeEach(() => {
  mockAuthenticatedFetch.mockReset();
  mockAuthenticatedFetch.mockResolvedValue(
    new Response(null, { status: 200 }),
  );
});

describe("createTiptapApi", () => {
  it("fetches document preferences with authenticated credentials", async () => {
    const api = createTiptapApi();
    await api.fetchPreferences("doc-123");

    expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
      "http://example.com/projects/doc-123/preferences",
    );
  });

  it("saves document preferences using PUT and JSON payload", async () => {
    const api = createTiptapApi();
    await api.savePreferences("doc-123", { lint: true });

    const [url, options] = mockAuthenticatedFetch.mock.calls[0];
    expect(url).toBe("http://example.com/projects/doc-123/preferences");
    expect(options).toMatchObject({ method: "PUT" });
    expect(options?.headers).toEqual({ "Content-Type": "application/json" });
    expect(options?.body).toBe(JSON.stringify({ lint: true }));
  });

  it("includes the X-User header when creating a revision", async () => {
    const api = createTiptapApi();
    await api.createRevision("doc-123", "alice", { content: "<p>Hi</p>" });

    const [url, options] = mockAuthenticatedFetch.mock.calls[0];
    expect(url).toBe("http://example.com/documents/doc-123/revisions");
    expect(options).toMatchObject({
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User": "alice",
      },
    });
    expect(options?.body).toBe(JSON.stringify({ content: "<p>Hi</p>" }));
  });

  it("requests revision listings with the acting username", async () => {
    const api = createTiptapApi();
    await api.fetchRevisions("doc-123", "bob");

    const [url, options] = mockAuthenticatedFetch.mock.calls[0];
    expect(url).toBe("http://example.com/documents/doc-123/revisions");
    expect(options).toEqual({ headers: { "X-User": "bob" } });
  });

  it("fetches document details for the editor", async () => {
    const api = createTiptapApi();
    await api.fetchDocument("doc-123");

    expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
      "http://example.com/documents/doc-123",
    );
  });

  it("fetches archive records and template content through the helper", async () => {
    const api = createTiptapApi();
    await api.fetchArchive("archive-1");
    await api.fetchTemplate("template-1");

    expect(mockAuthenticatedFetch).toHaveBeenNthCalledWith(
      1,
      "http://example.com/archive/archive-1",
    );
    expect(mockAuthenticatedFetch).toHaveBeenNthCalledWith(
      2,
      "http://example.com/templates/template-1",
    );
  });

  it("fetches starter content using the document-types route without API prefix", async () => {
    const api = createTiptapApi();
    await api.fetchStarterContent("Standard Operating Procedure");

    expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
      "/document-types/Standard%20Operating%20Procedure/starter-content",
    );
  });

  it("URL-encodes special characters in the doc-type for starter-content", async () => {
    const api = createTiptapApi();
    await api.fetchStarterContent("21 CFR / ISO");

    expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
      "/document-types/21%20CFR%20%2F%20ISO/starter-content",
    );
  });
});

describe("createWordTemplateApi", () => {
  it("lists templates via authenticatedFetch", async () => {
    const api = createWordTemplateApi();
    await api.listTemplates();

    expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
      "http://example.com/templates",
    );
  });
});

describe("createTemplateConfigApi", () => {
  it("loads document and email templates through authenticated fetch", async () => {
    const api = createTemplateConfigApi();
    await api.listTemplates();
    await api.listEmailTemplates();

    expect(mockAuthenticatedFetch).toHaveBeenNthCalledWith(
      1,
      "http://example.com/templates",
    );
    expect(mockAuthenticatedFetch).toHaveBeenNthCalledWith(
      2,
      "http://example.com/email-templates",
    );
  });

  it("sends DELETE requests for template removals", async () => {
    const api = createTemplateConfigApi();
    await api.deleteTemplate("tpl-1");
    await api.deleteEmailTemplate("welcome");

    expect(mockAuthenticatedFetch).toHaveBeenNthCalledWith(
      1,
      "http://example.com/templates/tpl-1",
      { method: "DELETE" },
    );
    expect(mockAuthenticatedFetch).toHaveBeenNthCalledWith(
      2,
      "http://example.com/email-templates/welcome",
      { method: "DELETE" },
    );
  });
});
