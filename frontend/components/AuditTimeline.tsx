"use client";

import Link from "next/link";
import React, { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";

export type AuditType = "approval" | "review" | "edit" | "phase";

export interface AuditEntry {
  id: string;
  timestamp: string;
  message: string;
  type: AuditType;
  link?: string;
}

interface Props {
  events: AuditEntry[];
}

const TYPE_LABELS: Record<AuditType, string> = {
  approval: "Approvals",
  review: "Reviews",
  edit: "Document edits",
  phase: "Phase changes",
};

export default function AuditTimeline({ events }: Props) {
  const [filters, setFilters] = useState<Record<AuditType, boolean>>({
    approval: true,
    review: true,
    edit: true,
    phase: true,
  });

  const filtered = useMemo(
    () => events.filter((e) => filters[e.type]),
    [events, filters],
  );

  const grouped = useMemo(() => {
    const map: Record<string, AuditEntry[]> = {};
    filtered.forEach((e) => {
      const day = e.timestamp.slice(0, 10);
      (map[day] ||= []).push(e);
    });
    return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
  }, [filtered]);

  const toggle = (type: AuditType) =>
    setFilters((f) => ({ ...f, [type]: !f[type] }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 text-sm">
        {(Object.keys(TYPE_LABELS) as AuditType[]).map((t) => (
          <label key={t} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={filters[t]}
              onChange={() => toggle(t)}
            />
            {TYPE_LABELS[t]}
          </label>
        ))}
      </div>
      {grouped.length === 0 && (
        <p className="text-sm text-gray-500">No audit events.</p>
      )}
      {grouped.map(([day, items]) => (
        <Card key={day}>
          <CardContent className="pt-4">
            <h3 className="mb-2 font-medium">
              {new Date(day).toLocaleDateString()}
            </h3>
            <ul className="space-y-1 text-sm">
              {items
                .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                .map((e) => (
                  <li key={e.id} className="flex gap-2">
                    <span className="w-16 text-gray-500">
                      {new Date(e.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    {e.link ? (
                      <Link href={e.link} className="text-blue-600 hover:underline">
                        {e.message}
                      </Link>
                    ) : (
                      <span>{e.message}</span>
                    )}
                  </li>
                ))}
            </ul>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

