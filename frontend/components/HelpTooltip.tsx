// frontend/components/HelpTooltip.tsx
// SPDX-License-Identifier: MIT
import React, { useState, useRef, useEffect } from "react";

interface HelpTooltipProps {
  /** The help text to display in the tooltip popover. */
  content: string;
  /** Optional URL to a documentation section. Renders a "Learn more" link. */
  href?: string;
  /** Controls the size of the trigger button icon. Defaults to "sm". */
  size?: "sm" | "md";
}

/**
 * A small circular `?` button that shows a styled tooltip popover on hover or
 * focus.  Keyboard-accessible: opens on focus/mouseenter, closes on
 * blur/mouseleave or Escape.
 *
 * Usage:
 *   <HelpTooltip content="Phase advancement requires all reviewers to submit." href="/help#phases" />
 */
export default function HelpTooltip({ content, href, size = "sm" }: HelpTooltipProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const iconSize = size === "md" ? "w-4 h-4" : "w-3.5 h-3.5";
  const btnSize = size === "md" ? "w-5 h-5" : "w-4 h-4";

  return (
    <span
      ref={containerRef}
      className="relative inline-flex items-center"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label="Help"
        aria-expanded={open}
        className={`${btnSize} rounded-full bg-gray-100 hover:bg-indigo-100 text-gray-500 hover:text-indigo-600 dark:bg-gray-700 dark:hover:bg-indigo-900 dark:text-gray-400 dark:hover:text-indigo-300 flex items-center justify-center flex-shrink-0 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1`}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={iconSize}
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </button>

      {open && (
        <div
          role="tooltip"
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg bg-gray-900 dark:bg-gray-800 text-white text-xs shadow-lg px-3 py-2 leading-relaxed pointer-events-none"
        >
          {/* Arrow */}
          <span
            className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0"
            style={{
              borderLeft: "6px solid transparent",
              borderRight: "6px solid transparent",
              borderTop: "6px solid rgb(17 24 39)", // gray-900
            }}
            aria-hidden="true"
          />
          <p className="mb-1">{content}</p>
          {href && (
            <a
              href={href}
              className="text-indigo-300 hover:text-indigo-200 underline pointer-events-auto"
              target="_blank"
              rel="noopener noreferrer"
              tabIndex={-1}
            >
              Learn more →
            </a>
          )}
        </div>
      )}
    </span>
  );
}
