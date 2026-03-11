/**
 * Offline storage utility for pending document drafts.
 *
 * Tries IndexedDB first; falls back to localStorage if IndexedDB is
 * unavailable (private-browsing quirks, older browsers, SSR).
 */

const DB_NAME = "docreview360-offline";
const STORE_NAME = "drafts";
const DB_VERSION = 1;

export interface OfflineDraft {
  docId: string;
  content: string;
  timestamp: number;
  syncPending: boolean;
}

// ---------------------------------------------------------------------------
// IndexedDB helpers
// ---------------------------------------------------------------------------

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "docId" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbPut(draft: OfflineDraft): Promise<void> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(draft);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

async function idbGet(docId: string): Promise<OfflineDraft | undefined> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).get(docId);
    req.onsuccess = () => { db.close(); resolve(req.result as OfflineDraft | undefined); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

async function idbDelete(docId: string): Promise<void> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(docId);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

async function idbGetAll(): Promise<OfflineDraft[]> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).getAll();
    req.onsuccess = () => { db.close(); resolve(req.result as OfflineDraft[]); };
    req.onerror = () => { db.close(); reject(req.error); };
  });
}

// ---------------------------------------------------------------------------
// localStorage fallback helpers
// ---------------------------------------------------------------------------

const LS_PREFIX = "docreview360:offline:";

function lsPut(draft: OfflineDraft): void {
  localStorage.setItem(LS_PREFIX + draft.docId, JSON.stringify(draft));
}

function lsGet(docId: string): OfflineDraft | undefined {
  const raw = localStorage.getItem(LS_PREFIX + docId);
  if (!raw) return undefined;
  try { return JSON.parse(raw) as OfflineDraft; } catch { return undefined; }
}

function lsDelete(docId: string): void {
  localStorage.removeItem(LS_PREFIX + docId);
}

function lsGetAll(): OfflineDraft[] {
  const results: OfflineDraft[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith(LS_PREFIX)) {
      const raw = localStorage.getItem(key);
      if (raw) {
        try { results.push(JSON.parse(raw) as OfflineDraft); } catch { /* skip */ }
      }
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Feature-detect IndexedDB availability
// ---------------------------------------------------------------------------

function isIdbAvailable(): boolean {
  return typeof window !== "undefined" && typeof window.indexedDB !== "undefined";
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Persist a draft locally, marking it as pending sync.
 */
export async function saveOfflineDraft(docId: string, content: string): Promise<void> {
  if (typeof window === "undefined") return;
  const draft: OfflineDraft = { docId, content, timestamp: Date.now(), syncPending: true };
  if (isIdbAvailable()) {
    try { await idbPut(draft); return; } catch { /* fall through */ }
  }
  lsPut(draft);
}

/**
 * Load the most recent local draft for a document.
 * Returns null if no draft exists.
 */
export async function loadOfflineDraft(
  docId: string,
): Promise<{ content: string; timestamp: number } | null> {
  if (typeof window === "undefined") return null;
  let draft: OfflineDraft | undefined;
  if (isIdbAvailable()) {
    try { draft = await idbGet(docId); } catch { /* fall through */ }
  }
  if (!draft) draft = lsGet(docId);
  if (!draft) return null;
  return { content: draft.content, timestamp: draft.timestamp };
}

/**
 * Mark a draft as successfully synced (syncPending = false).
 * Call this after a successful PUT /documents/{id}.
 */
export async function markSynced(docId: string): Promise<void> {
  if (typeof window === "undefined") return;
  let draft: OfflineDraft | undefined;
  if (isIdbAvailable()) {
    try { draft = await idbGet(docId); } catch { /* fall through */ }
  }
  if (!draft) draft = lsGet(docId);
  if (!draft) return;
  const updated: OfflineDraft = { ...draft, syncPending: false };
  if (isIdbAvailable()) {
    try { await idbPut(updated); return; } catch { /* fall through */ }
  }
  lsPut(updated);
}

/**
 * Return all drafts that still have syncPending = true.
 */
export async function getPendingDrafts(): Promise<Array<{ docId: string; timestamp: number }>> {
  if (typeof window === "undefined") return [];
  let all: OfflineDraft[] = [];
  if (isIdbAvailable()) {
    try { all = await idbGetAll(); } catch { /* fall through */ }
  }
  if (!all.length) all = lsGetAll();
  return all
    .filter((d) => d.syncPending)
    .map((d) => ({ docId: d.docId, timestamp: d.timestamp }));
}

/**
 * Permanently remove a stored draft (e.g. after successful sync or discard).
 */
export async function clearDraft(docId: string): Promise<void> {
  if (typeof window === "undefined") return;
  if (isIdbAvailable()) {
    try { await idbDelete(docId); } catch { /* fall through */ }
  }
  lsDelete(docId);
}
