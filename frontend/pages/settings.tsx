import React from "react";
import Link from "next/link";

const CONFIG_ITEMS = [
  { label: "Workflows", href: "/workflows" },
  { label: "Document Types", href: "/document-types" },
  { label: "Phases", href: "/phases" },
  { label: "Templates", href: "/templates" },
  { label: "User Management", href: "/user-management" },
  { label: "Permissions", href: "/permissions" },
  { label: "Audit Logs", href: "/audit-logs" },
  { label: "App Settings", href: "/app-settings" },
  { label: "Integrations", href: "/integrations" },
];

export default function ConfigurationPage() {
  return (
    <div className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">Configuration</h1>
      <ul className="list-disc space-y-2 pl-6">
        {CONFIG_ITEMS.map((item) => (
          <li key={item.href}>
            <Link href={item.href} className="text-indigo-700 underline">
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
