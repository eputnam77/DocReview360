/**
 * LocaleSwitcher — dropdown that lets users switch the UI language.
 *
 * Uses the useTranslation hook to read the current locale and call setLocale
 * when the user picks a new one.
 */
import React from "react";
import { useTranslation } from "../lib/useTranslation";

interface LocaleOption {
  code: string;
  label: string;
}

const LOCALE_OPTIONS: LocaleOption[] = [
  { code: "en", label: "\uD83C\uDDFA\uD83C\uDDF8 English" },
  { code: "es", label: "\uD83C\uDDEA\uD83C\uDDF8 Espa\u00F1ol" },
  { code: "fr", label: "\uD83C\uDDEB\uD83C\uDDF7 Fran\u00E7ais" },
  { code: "de", label: "\uD83C\uDDE9\uD83C\uDDEA Deutsch" },
];

export default function LocaleSwitcher() {
  const { locale, setLocale } = useTranslation();

  function handleChange(event: React.ChangeEvent<HTMLSelectElement>) {
    setLocale(event.target.value);
  }

  return (
    <select
      value={locale}
      onChange={handleChange}
      aria-label="Select language"
      style={{
        padding: "4px 8px",
        borderRadius: "4px",
        border: "1px solid #d1d5db",
        background: "white",
        fontSize: "0.875rem",
        cursor: "pointer",
      }}
    >
      {LOCALE_OPTIONS.map((opt) => (
        <option key={opt.code} value={opt.code}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
