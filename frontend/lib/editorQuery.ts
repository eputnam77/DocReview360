export function readSingleQueryParam(
  value: string | string[] | undefined,
): string | undefined {
  const candidate = Array.isArray(value) ? value[0] : value;
  if (typeof candidate !== "string") {
    return undefined;
  }
  const trimmed = candidate.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

export function readBooleanQueryParam(
  value: string | string[] | undefined,
): boolean {
  const candidate = readSingleQueryParam(value);
  if (!candidate) {
    return false;
  }
  const normalized = candidate.toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes";
}
