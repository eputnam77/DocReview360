const ALLOWED_TAGS = new Set([
  "a",
  "abbr",
  "b",
  "blockquote",
  "br",
  "caption",
  "code",
  "col",
  "colgroup",
  "dd",
  "del",
  "div",
  "dl",
  "dt",
  "em",
  "figcaption",
  "figure",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "hr",
  "i",
  "img",
  "li",
  "mark",
  "ol",
  "p",
  "pre",
  "s",
  "span",
  "strong",
  "sub",
  "sup",
  "table",
  "tbody",
  "td",
  "tfoot",
  "th",
  "thead",
  "tr",
  "u",
  "ul",
]);

const DROP_WITH_CONTENT = new Set([
  "base",
  "button",
  "canvas",
  "embed",
  "form",
  "iframe",
  "input",
  "link",
  "math",
  "meta",
  "object",
  "script",
  "select",
  "source",
  "style",
  "svg",
  "textarea",
  "track",
]);

const GLOBAL_ATTRIBUTES = new Set(["class", "dir", "lang", "role", "title"]);

const TAG_ATTRIBUTES: Record<string, ReadonlySet<string>> = {
  a: new Set(["href", "rel", "target"]),
  col: new Set(["span"]),
  img: new Set(["alt", "height", "src", "width"]),
  ol: new Set(["start", "type"]),
  table: new Set(["summary"]),
  td: new Set(["colspan", "headers", "rowspan"]),
  th: new Set(["abbr", "colspan", "headers", "rowspan", "scope"]),
};

const SAFE_DATA_IMAGE_PREFIXES = [
  "data:image/gif;base64,",
  "data:image/jpeg;base64,",
  "data:image/png;base64,",
  "data:image/webp;base64,",
];

function allowsAttribute(tagName: string, attributeName: string): boolean {
  if (
    GLOBAL_ATTRIBUTES.has(attributeName) ||
    attributeName.startsWith("aria-") ||
    attributeName.startsWith("data-")
  ) {
    return true;
  }

  return TAG_ATTRIBUTES[tagName]?.has(attributeName) ?? false;
}

function isSafeUrl(value: string, attributeName: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) {
    return false;
  }

  const lowered = trimmed.toLowerCase();
  if (lowered.startsWith("javascript:") || lowered.startsWith("vbscript:") || lowered.startsWith("file:")) {
    return false;
  }

  if (lowered.startsWith("data:")) {
    return attributeName === "src" && SAFE_DATA_IMAGE_PREFIXES.some((prefix) => lowered.startsWith(prefix));
  }

  try {
    const base = window.location?.href || "https://docreview360.invalid/";
    const parsed = new URL(trimmed, base);
    if (attributeName === "src") {
      return parsed.protocol === "http:" || parsed.protocol === "https:";
    }
    return ["http:", "https:", "mailto:", "tel:"].includes(parsed.protocol);
  } catch {
    return false;
  }
}

function sanitizeNode(node: Node, outputDocument: Document): Node | null {
  if (node.nodeType === Node.TEXT_NODE) {
    return outputDocument.createTextNode(node.textContent || "");
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }

  const sourceElement = node as Element;
  const tagName = sourceElement.tagName.toLowerCase();
  if (DROP_WITH_CONTENT.has(tagName)) {
    return null;
  }

  if (!ALLOWED_TAGS.has(tagName)) {
    const fragment = outputDocument.createDocumentFragment();
    for (const child of Array.from(sourceElement.childNodes)) {
      const sanitizedChild = sanitizeNode(child, outputDocument);
      if (sanitizedChild) {
        fragment.appendChild(sanitizedChild);
      }
    }
    return fragment;
  }

  const cleanElement = outputDocument.createElement(tagName);
  for (const attribute of Array.from(sourceElement.attributes)) {
    const attributeName = attribute.name.toLowerCase();
    if (!allowsAttribute(tagName, attributeName)) {
      continue;
    }
    if ((attributeName === "href" || attributeName === "src") && !isSafeUrl(attribute.value, attributeName)) {
      continue;
    }
    if (attributeName === "target" && !["_blank", "_parent", "_self", "_top"].includes(attribute.value)) {
      continue;
    }
    cleanElement.setAttribute(attributeName, attribute.value);
  }

  if (tagName === "a" && cleanElement.getAttribute("target") === "_blank") {
    cleanElement.setAttribute("rel", "noopener noreferrer");
  }

  for (const child of Array.from(sourceElement.childNodes)) {
    const sanitizedChild = sanitizeNode(child, outputDocument);
    if (sanitizedChild) {
      cleanElement.appendChild(sanitizedChild);
    }
  }

  return cleanElement;
}

export default function sanitizeHtml(html: string): string {
  if (typeof DOMParser === "undefined" || typeof document === "undefined" || typeof window === "undefined") {
    return "";
  }

  const parsed = new DOMParser().parseFromString(html, "text/html");
  const outputDocument = document.implementation.createHTMLDocument("");
  const fragment = outputDocument.createDocumentFragment();

  for (const child of Array.from(parsed.body.childNodes)) {
    const sanitizedChild = sanitizeNode(child, outputDocument);
    if (sanitizedChild) {
      fragment.appendChild(sanitizedChild);
    }
  }

  outputDocument.body.appendChild(fragment);
  return outputDocument.body.innerHTML;
}
