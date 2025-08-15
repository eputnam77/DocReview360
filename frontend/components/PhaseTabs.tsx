// frontend/components/PhaseTabs.tsx

import React, { useRef } from "react";
import { cn } from "@/lib/utils";

interface Phase {
  id: string;
  label: string;
}

export interface PhaseTabsProps {
  phases: Phase[];
  activePhaseId?: string | null;
  counts?: Record<string, number>;
  onChange?: (id: string) => void;
}

export default function PhaseTabs({
  phases,
  activePhaseId,
  counts = {},
  onChange,
}: PhaseTabsProps) {
  const tabsRef = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (!onChange || phases.length === 0) return;
    const idx = phases.findIndex((p) => p.id === activePhaseId);
    let newIdx = idx;
    if (e.key === "ArrowRight") {
      newIdx = (idx + 1) % phases.length;
    } else if (e.key === "ArrowLeft") {
      newIdx = (idx - 1 + phases.length) % phases.length;
    } else if (e.key === "Home") {
      newIdx = 0;
    } else if (e.key === "End") {
      newIdx = phases.length - 1;
    } else {
      return;
    }
    e.preventDefault();
    const newPhase = phases[newIdx];
    if (newPhase) {
      onChange(newPhase.id);
      tabsRef.current[newIdx]?.focus();
    }
  };

  return (
    <div
      role="tablist"
      aria-orientation="horizontal"
      className="flex gap-1"
      onKeyDown={handleKeyDown}
    >
      {phases.map((p, i) => {
        const isActive = activePhaseId === p.id;
        const count = counts[p.id];
        return (
          <button
            key={p.id}
            ref={(el) => {
              tabsRef.current[i] = el;
            }}
            role="tab"
            id={`phase-tab-${p.id}`}
            aria-selected={isActive}
            aria-controls={`phase-panel-${p.id}`}
            tabIndex={isActive ? 0 : -1}
            className={cn(
              "px-3 py-1.5 text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2",
              isActive
                ? "bg-indigo-600 text-white"
                : "bg-transparent text-gray-600 hover:bg-gray-100 hover:text-indigo-600",
              !onChange && "cursor-default opacity-60",
            )}
            onClick={() => onChange?.(p.id)}
            disabled={!onChange}
          >
            <span>{p.label}</span>
            {typeof count === "number" && (
              <span className="ml-1 text-xs">({count})</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

