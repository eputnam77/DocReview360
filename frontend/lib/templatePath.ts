export function encodeTemplateNameForPath(name: string): string {
  return encodeURIComponent(name);
}

export function buildTemplateUrlPath(name: string, suffix = ""): string {
  const normalizedSuffix = suffix
    ? suffix.startsWith("/")
      ? suffix
      : `/${suffix}`
    : "";
  return `/templates/${encodeTemplateNameForPath(name)}${normalizedSuffix}`;
}
