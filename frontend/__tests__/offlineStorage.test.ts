/**
 * Item 41 Phase 2 — Offline editing support tests.
 *
 * Tests for:
 *  - offlineStorage.ts (localStorage fallback path used by jsdom)
 *  - saveOfflineDraft / loadOfflineDraft / markSynced / getPendingDrafts / clearDraft
 *
 * Note: IndexedDB is not available in jsdom, so the localStorage fallback path
 * is exercised automatically — this is the exact path used in private-browsing
 * and older environments.
 */
import { beforeEach, describe, expect, it } from "vitest";

// Provide a minimal IndexedDB stub that throws so the IDB path is skipped and
// the localStorage fallback is exercised in all tests.
Object.defineProperty(globalThis, "indexedDB", {
  value: undefined,
  writable: true,
  configurable: true,
});

import {
  clearDraft,
  getPendingDrafts,
  loadOfflineDraft,
  markSynced,
  saveOfflineDraft,
} from "@/lib/offlineStorage";

const LS_PREFIX = "docreview360:offline:";

beforeEach(() => {
  // Clear only offline draft keys to avoid polluting other tests.
  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith(LS_PREFIX)) keysToRemove.push(key);
  }
  keysToRemove.forEach((k) => localStorage.removeItem(k));
});

// ---------------------------------------------------------------------------
// saveOfflineDraft
// ---------------------------------------------------------------------------

describe("saveOfflineDraft", () => {
  it("persists a draft to localStorage", async () => {
    await saveOfflineDraft("doc-1", "<p>Hello</p>");
    const raw = localStorage.getItem(LS_PREFIX + "doc-1");
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw!);
    expect(parsed.docId).toBe("doc-1");
    expect(parsed.content).toBe("<p>Hello</p>");
    expect(parsed.syncPending).toBe(true);
  });

  it("overwrites an existing draft for the same docId", async () => {
    await saveOfflineDraft("doc-overwrite", "<p>v1</p>");
    await saveOfflineDraft("doc-overwrite", "<p>v2</p>");
    const raw = localStorage.getItem(LS_PREFIX + "doc-overwrite");
    const parsed = JSON.parse(raw!);
    expect(parsed.content).toBe("<p>v2</p>");
  });

  it("stores a numeric timestamp", async () => {
    const before = Date.now();
    await saveOfflineDraft("doc-ts", "<p>ts</p>");
    const after = Date.now();
    const raw = localStorage.getItem(LS_PREFIX + "doc-ts");
    const parsed = JSON.parse(raw!);
    expect(parsed.timestamp).toBeGreaterThanOrEqual(before);
    expect(parsed.timestamp).toBeLessThanOrEqual(after);
  });
});

// ---------------------------------------------------------------------------
// loadOfflineDraft
// ---------------------------------------------------------------------------

describe("loadOfflineDraft", () => {
  it("returns null for an unknown docId", async () => {
    const result = await loadOfflineDraft("nonexistent-doc");
    expect(result).toBeNull();
  });

  it("returns the content and timestamp for a saved draft", async () => {
    await saveOfflineDraft("doc-load", "<p>Content</p>");
    const result = await loadOfflineDraft("doc-load");
    expect(result).not.toBeNull();
    expect(result!.content).toBe("<p>Content</p>");
    expect(result!.timestamp).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// markSynced
// ---------------------------------------------------------------------------

describe("markSynced", () => {
  it("sets syncPending to false after marking synced", async () => {
    await saveOfflineDraft("doc-synced", "<p>Synced</p>");
    await markSynced("doc-synced");
    const raw = localStorage.getItem(LS_PREFIX + "doc-synced");
    const parsed = JSON.parse(raw!);
    expect(parsed.syncPending).toBe(false);
  });

  it("is a no-op for an unknown docId (does not throw)", async () => {
    await expect(markSynced("unknown-doc")).resolves.toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// getPendingDrafts
// ---------------------------------------------------------------------------

describe("getPendingDrafts", () => {
  it("returns an empty array when no drafts exist", async () => {
    const pending = await getPendingDrafts();
    expect(pending).toEqual([]);
  });

  it("returns pending drafts as {docId, timestamp} objects", async () => {
    await saveOfflineDraft("doc-pending-a", "<p>A</p>");
    await saveOfflineDraft("doc-pending-b", "<p>B</p>");
    const pending = await getPendingDrafts();
    const ids = pending.map((d) => d.docId).sort();
    expect(ids).toContain("doc-pending-a");
    expect(ids).toContain("doc-pending-b");
    pending.forEach((d) => expect(typeof d.timestamp).toBe("number"));
  });

  it("excludes drafts that have been marked as synced", async () => {
    await saveOfflineDraft("doc-synced-exclude", "<p>X</p>");
    await markSynced("doc-synced-exclude");
    const pending = await getPendingDrafts();
    expect(pending.map((d) => d.docId)).not.toContain("doc-synced-exclude");
  });
});

// ---------------------------------------------------------------------------
// clearDraft
// ---------------------------------------------------------------------------

describe("clearDraft", () => {
  it("removes the draft from localStorage", async () => {
    await saveOfflineDraft("doc-clear", "<p>To clear</p>");
    await clearDraft("doc-clear");
    expect(localStorage.getItem(LS_PREFIX + "doc-clear")).toBeNull();
  });

  it("is a no-op when the draft does not exist (does not throw)", async () => {
    await expect(clearDraft("does-not-exist")).resolves.toBeUndefined();
  });

  it("removes the draft from getPendingDrafts after clearing", async () => {
    await saveOfflineDraft("doc-remove", "<p>Bye</p>");
    await clearDraft("doc-remove");
    const pending = await getPendingDrafts();
    expect(pending.map((d) => d.docId)).not.toContain("doc-remove");
  });
});
