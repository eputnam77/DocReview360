"use client";
import Link from "next/link";
import React, { forwardRef, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
const TYPE_LABELS = {
    approval: "Approvals",
    review: "Reviews",
    edit: "Document edits",
    phase: "Phase changes",
};
const APPROVAL_EVENT_LABELS = {
    signature_verified: "Signature verified",
    signature_hash_mismatch: "Signature hash mismatch",
    signature_invalid: "Signature invalid",
    signature_requested: "Signature requested",
    approval_revoked: "Approval revoked",
};
const formatMessage = (e) => e.type === "approval"
    ? APPROVAL_EVENT_LABELS[e.message] || e.message
    : e.message;
const AuditTimeline = forwardRef(({ events }, ref) => {
    const [filters, setFilters] = useState({
        approval: true,
        review: true,
        edit: true,
        phase: true,
    });
    const filtered = useMemo(() => events.filter((e) => filters[e.type]), [events, filters]);
    const grouped = useMemo(() => {
        const map = {};
        filtered.forEach((e) => {
            const day = e.timestamp.slice(0, 10);
            (map[day] ||= []).push(e);
        });
        return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
    }, [filtered]);
    const toggle = (type) => setFilters((f) => ({ ...f, [type]: !f[type] }));
    return (<div ref={ref} className="space-y-4">
      <div className="flex flex-wrap gap-2 text-sm">
        {Object.keys(TYPE_LABELS).map((t) => (<label key={t} className="flex items-center gap-1">
            <input type="checkbox" checked={filters[t]} onChange={() => toggle(t)}/>
            {TYPE_LABELS[t]}
          </label>))}
      </div>
      {grouped.length === 0 && (<p className="text-sm text-gray-500">No audit events.</p>)}
      {grouped.map(([day, items]) => (<Card key={day}>
          <CardContent className="pt-4">
            <h3 className="mb-2 font-medium">
              {new Date(day).toLocaleDateString()}
            </h3>
            <ul className="space-y-1 text-sm">
              {items
                .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                .map((e) => (<li key={e.id} className="flex gap-2">
                    <span className="w-16 text-gray-500">
                      {new Date(e.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                })}
                    </span>
                    {e.link ? (<Link href={e.link} className="text-blue-600 hover:underline">
                        {formatMessage(e)}
                      </Link>) : (<span>{formatMessage(e)}</span>)}
                  </li>))}
            </ul>
          </CardContent>
        </Card>))}
    </div>);
});
AuditTimeline.displayName = "AuditTimeline";
export default AuditTimeline;
