// Sticky navigation bar for the project detail page.
// Extracted from pages/projects/[id]/index.tsx (R-09).

import React from "react";

export const NAV = [
  { id: "overview", label: "Overview" },
  { id: "reviewers", label: "Reviewers" },
  { id: "feedback", label: "Feedback" },
  { id: "signatures", label: "Signatures" },
  { id: "approvals", label: "Approvals" },
  { id: "history", label: "History" },
];

export function StickyNav() {
  const [active, setActive] = React.useState(NAV[0].id);
  const linksRef = React.useRef<(HTMLAnchorElement | null)[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLUListElement>) => {
    const idx = NAV.findIndex((n) => n.id === active);
    let newIdx = idx;
    if (e.key === "ArrowRight") {
      newIdx = (idx + 1) % NAV.length;
    } else if (e.key === "ArrowLeft") {
      newIdx = (idx - 1 + NAV.length) % NAV.length;
    } else if (e.key === "Home") {
      newIdx = 0;
    } else if (e.key === "End") {
      newIdx = NAV.length - 1;
    } else {
      return;
    }
    e.preventDefault();
    const newTab = NAV[newIdx];
    setActive(newTab.id);
    linksRef.current[newIdx]?.focus();
  };

  return (
    <nav className="sticky top-0 z-30 bg-white/80 dark:bg-gray-900/80 backdrop-blur supports-backdrop-blur:border-b supports-backdrop-blur:border-gray-200 dark:supports-backdrop-blur:border-gray-700">
      <ul
        role="tablist"
        className="flex gap-6 px-8 py-2 text-sm font-medium overflow-x-auto scrollbar-hide"
        onKeyDown={handleKeyDown}
      >
        {NAV.map((s, i) => (
          <li key={s.id}>
            <a
              ref={(el) => {
                linksRef.current[i] = el;
              }}
              role="tab"
              id={`nav-${s.id}`}
              aria-selected={active === s.id}
              tabIndex={active === s.id ? 0 : -1}
              href={`#${s.id}`}
              className="hover:text-indigo-600 dark:hover:text-indigo-400 text-gray-600 dark:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              onClick={() => setActive(s.id)}
              onKeyDown={(e) => {
                if (e.key === " " || e.key === "Enter") {
                  e.preventDefault();
                  setActive(s.id);
                  linksRef.current[i]?.click();
                }
              }}
            >
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
