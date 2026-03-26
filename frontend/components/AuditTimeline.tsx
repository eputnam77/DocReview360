"use client";

import Link from "next/link";
import React, { forwardRef, useMemo, useState } from "react";
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

const APPROVAL_EVENT_LABELS: Record<string, string> = {
  signature_verified: "Signature verified",
  signature_hash_mismatch: "Signature hash mismatch",
  signature_invalid: "Signature invalid",
  signature_requested: "Signature requested",
  approval_revoked: "Approval revoked",
  approved: "Approved",
  rejected: "Rejected",
  reset: "Approval reset",
};

// Map raw backend event names (dot-notation or snake_case) to human-readable
// descriptions so audit history shows "Alice submitted feedback" rather than
// "feedback.submitted".
const REVIEW_EVENT_LABELS: Record<string, string> = {
  "feedback.submitted": "Reviewer submitted feedback",
  "feedback.replied": "Reply posted to feedback",
  "feedback.accepted": "Feedback accepted",
  "feedback.rejected": "Feedback rejected",
  "feedback.resolved": "Feedback resolved",
  "feedback.created": "Feedback item created",
  review_submitted: "Reviewer submitted feedback",
  review_started: "Reviewer started review",
  review_completed: "Review completed",
  review_assigned: "Reviewer assigned",
  reviewer_added: "Reviewer added",
  reviewer_removed: "Reviewer removed",
  concurrence_granted: "Reviewer concurred",
  concurrence_withheld: "Reviewer non-concurred",
  phase_advanced: "Phase advanced",
  phase_changed: "Phase changed",
  project_created: "Project created",
  document_uploaded: "Document uploaded",
  document_updated: "Document updated",
  read: "Record accessed",
  create_project: "Project created",
  list_workflows_endpoint: "Workflow list viewed",
};

function humaniseMessage(message: string): string {
  if (REVIEW_EVENT_LABELS[message]) return REVIEW_EVENT_LABELS[message];
  // Convert dot notation and snake_case to Title Case words
  return message
    .replace(/[._]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const formatMessage = (e: AuditEntry): string => {
  if (e.type === "approval") {
    return APPROVAL_EVENT_LABELS[e.message] ?? humaniseMessage(e.message);
  }
  return humaniseMessage(e.message);
};

// Parse a UTC timestamp string safely. Backend timestamps may omit the 'Z'
// suffix; we always treat them as UTC to avoid timezone-shift bugs when
// grouping by day or displaying times.
function parseUtcTimestamp(ts: string): Date {
  if (!ts) return new Date(0);
  // Already has timezone info
  if (ts.includes("+") || ts.endsWith("Z")) return new Date(ts);
  // No timezone suffix — assume UTC
  return new Date(ts + "Z");
}

// Format a UTC timestamp for display in the user's local timezone but make
// the grouping key (YYYY-MM-DD) always based on UTC date to avoid
// cross-midnight flicker.
function utcDayKey(ts: string): string {
  const d = parseUtcTimestamp(ts);
  // Zero-pad month and day
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

const AuditTimeline = forwardRef<HTMLDivElement, Props>(({ events }, ref) => {
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
      const day = utcDayKey(e.timestamp);
      (map[day] ||= []).push(e);
    });
    return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
  }, [filtered]);

  const toggle = (type: AuditType) =>
    setFilters((f) => ({ ...f, [type]: !f[type] }));

  return (
    <div ref={ref} className="space-y-4">
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
              {parseUtcTimestamp(day + "T00:00:00Z").toLocaleDateString(undefined, {
                timeZone: "UTC",
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </h3>
            <ul className="space-y-1 text-sm">
              {items
                .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                .map((e) => (
                  <li key={e.id} className="flex gap-2">
                    <span className="w-16 flex-shrink-0 text-gray-500">
                      {parseUtcTimestamp(e.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        timeZoneName: "short",
                      })}
                    </span>
                    {e.link ? (
                      <Link href={e.link} className="text-blue-600 hover:underline">
                        {formatMessage(e)}
                      </Link>
                    ) : (
                      <span>{formatMessage(e)}</span>
                    )}
                  </li>
                ))}
            </ul>
          </CardContent>
        </Card>
      ))}
    </div>
  );
});

AuditTimeline.displayName = "AuditTimeline";

export default AuditTimeline;
