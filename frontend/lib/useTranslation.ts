/**
 * useTranslation — locale-aware translation hook.
 *
 * - Reads/writes the active locale from localStorage key "docreview360_locale"
 * - Fetches translation strings from GET /i18n/translations/{locale}
 * - Returns { t, locale, setLocale, isLoading }
 */
import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";

const LOCALE_STORAGE_KEY = "docreview360_locale";
const DEFAULT_LOCALE = "en";

/** Resolve the current locale from localStorage (SSR-safe). */
function _readLocale(): string {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  return window.localStorage.getItem(LOCALE_STORAGE_KEY) ?? DEFAULT_LOCALE;
}

/**
 * Shape returned by the backend GET /i18n/translations/{locale} endpoint.
 * The `strings` object uses dot-notation keys, e.g. "nav.dashboard".
 */
interface TranslationsResponse {
  locale: string;
  strings: Record<string, string>;
}

function _normaliseLocaleTag(locale: string): string {
  const base = locale.trim().toLowerCase().split("-")[0]?.split("_")[0];
  return base || DEFAULT_LOCALE;
}

export function _flattenNestedStrings(
  input: Record<string, unknown>,
  prefix = "",
): Record<string, string> {
  const flattened: Record<string, string> = {};
  for (const [key, value] of Object.entries(input)) {
    const nextKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") {
      flattened[nextKey] = value;
      continue;
    }
    if (value && typeof value === "object" && !Array.isArray(value)) {
      Object.assign(
        flattened,
        _flattenNestedStrings(value as Record<string, unknown>, nextKey),
      );
    }
  }
  return flattened;
}

async function _loadPublicLocaleStrings(locale: string): Promise<Record<string, string>> {
  try {
    const normalized = _normaliseLocaleTag(locale);
    const res = await fetch(`/locales/${normalized}/common.json`, {
      credentials: "same-origin",
    });
    if (!res.ok) {
      return {};
    }
    const data = (await res.json()) as Record<string, unknown>;
    return _flattenNestedStrings(data);
  } catch {
    return {};
  }
}

/** Recursively get a nested value from an object using dot-notation key.
 * @internal exported for testing */
export function _dotGet(obj: Record<string, unknown>, key: string): string | undefined {
  const parts = key.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || typeof current !== "object") return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === "string" ? current : undefined;
}

/** Build a nested object from flat dot-notation keys for deep lookup.
 * @internal exported for testing */
export function _buildNested(flat: Record<string, string>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(flat)) {
    const parts = key.split(".");
    let node: Record<string, unknown> = result;
    for (let i = 0; i < parts.length - 1; i++) {
      if (typeof node[parts[i]] !== "object" || node[parts[i]] === null) {
        node[parts[i]] = {};
      }
      node = node[parts[i]] as Record<string, unknown>;
    }
    node[parts[parts.length - 1]] = value;
  }
  return result;
}

export interface UseTranslationResult {
  /** Translate a dot-notation key, returning fallback (or the key itself) when not found. */
  t: (key: string, fallback?: string) => string;
  /** Currently active locale code, e.g. "en", "es". */
  locale: string;
  /** Switch locale, persist to localStorage, sync to backend, and refresh translations. */
  setLocale: (locale: string) => void;
  /** True while translations are being fetched. */
  isLoading: boolean;
}

/**
 * Primary i18n hook.
 *
 * @param orgId  Optional organisation ID. When provided, translations are fetched
 *               from ``GET /i18n/terminology/{locale}?org_id={orgId}`` so that
 *               org-specific terminology overrides (e.g. "Project" → "Case") are
 *               applied on top of the base locale strings.
 *
 * Usage:
 *   const { t, locale, setLocale, isLoading } = useTranslation();
 *   const { t } = useTranslation({ orgId: "acme" });
 *   <span>{t("nav.dashboard")}</span>
 */
export function useTranslation(options?: { orgId?: string }): UseTranslationResult {
  const orgId = options?.orgId;
  const queryClient = useQueryClient();
  const locale = _readLocale();
  // Include orgId in the query key so each org's overrides are cached separately.
  const queryKey = orgId
    ? (["i18n-terminology", locale, orgId] as const)
    : (["i18n-translations", locale] as const);

  const { data, isLoading } = useQuery<TranslationsResponse>({
    queryKey,
    queryFn: async () => {
      const url = orgId
        ? `/i18n/terminology/${locale}?org_id=${encodeURIComponent(orgId)}`
        : `/i18n/translations/${locale}`;
      try {
        const res = await authenticatedFetch(url);
        if (res.ok) {
          return res.json() as Promise<TranslationsResponse>;
        }
      } catch {
        // Fall through to the public locale bundle for logged-out pages.
      }
      const publicStrings = await _loadPublicLocaleStrings(locale);
      return { locale: _normaliseLocaleTag(locale), strings: publicStrings };
    },
    // Cache translations for 5 minutes; they rarely change during a session.
    staleTime: 5 * 60 * 1000,
  });

  // Build a nested lookup tree once from the flat string map.
  const nested = _buildNested(data?.strings ?? {});

  const t = useCallback(
    (key: string, fallback?: string): string => {
      // 1. Try nested lookup (supports both "nav.dashboard" and flat keys)
      const nested_value = _dotGet(nested, key);
      if (nested_value !== undefined) return nested_value;
      // 2. Try direct flat lookup from backend response
      if (data?.strings?.[key] !== undefined) return data.strings[key];
      // 3. Return explicit fallback, or the key itself as last resort
      return fallback ?? key;
    },
    [nested, data],
  );

  const setLocale = useCallback(
    (newLocale: string) => {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(LOCALE_STORAGE_KEY, newLocale);
      }
      // Persist locale preference to backend (fire-and-forget; non-blocking)
      authenticatedFetch("/users/me/locale", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ locale: newLocale }),
      }).catch(() => {
        // Ignore errors — locale is still saved locally even if backend call fails.
      });
      // Invalidate locale queries (both plain translations and terminology-merged).
      queryClient.invalidateQueries({ queryKey: ["i18n-translations"] });
      queryClient.invalidateQueries({ queryKey: ["i18n-terminology"] });
    },
    [queryClient],
  );

  return { t, locale, setLocale, isLoading };
}
