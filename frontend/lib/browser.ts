export function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof document !== "undefined";
}

export function readLocalStorage(
  key: string,
  storage: Pick<Storage, "getItem"> | null = typeof window !== "undefined" ? window.localStorage : null,
): string | null {
  if (!storage) {
    return null;
  }
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

export function writeLocalStorage(
  key: string,
  value: string,
  storage: Pick<Storage, "setItem"> | null = typeof window !== "undefined" ? window.localStorage : null,
): boolean {
  if (!storage) {
    return false;
  }
  try {
    storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

export function removeLocalStorage(
  key: string,
  storage: Pick<Storage, "removeItem"> | null = typeof window !== "undefined" ? window.localStorage : null,
): boolean {
  if (!storage) {
    return false;
  }
  try {
    storage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

export function promptInBrowser(
  message: string,
  prompter: ((message?: string) => string | null) | null =
    typeof window !== "undefined" ? window.prompt.bind(window) : null,
): string | null {
  if (!prompter) {
    return null;
  }
  return prompter(message);
}

export function reloadCurrentPage(
  reloader: (() => void) | null =
    typeof window !== "undefined" ? window.location.reload.bind(window.location) : null,
): boolean {
  if (!reloader) {
    return false;
  }
  reloader();
  return true;
}

export function resolveBrowserUrl(
  value: string,
  origin: string | null = typeof window !== "undefined" ? window.location.origin : null,
): URL | null {
  if (!origin) {
    return null;
  }
  try {
    return new URL(value, origin);
  } catch {
    return null;
  }
}

export function assignBrowserLocation(
  href: string,
  assigner: ((href: string) => void) | null =
    typeof window !== "undefined" ? window.location.assign.bind(window.location) : null,
): boolean {
  if (!assigner) {
    return false;
  }
  assigner(href);
  return true;
}

export function downloadBrowserBlob(
  blob: Blob,
  filename: string,
  doc: Pick<Document, "createElement"> | null = typeof document !== "undefined" ? document : null,
  urlApi: Pick<typeof URL, "createObjectURL" | "revokeObjectURL"> | null = typeof URL !== "undefined" ? URL : null,
): boolean {
  if (!doc || !urlApi) {
    return false;
  }
  const href = urlApi.createObjectURL(blob);
  try {
    const anchor = doc.createElement("a");
    anchor.href = href;
    anchor.download = filename;
    anchor.click();
    return true;
  } finally {
    urlApi.revokeObjectURL(href);
  }
}
