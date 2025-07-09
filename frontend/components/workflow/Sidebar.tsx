// frontend/components/workflow/Sidebar.tsx

import React from "react";
import { useRouter } from "next/navigation";
import {
  Sparkle,
  Ticket,
  Inbox,
  Workflow,
  FileText,
  Users2,
  BarChart2,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { icon: <Ticket className="h-4 w-4" />, label: "Tickets", href: "/tickets" },
  { icon: <Inbox className="h-4 w-4" />, label: "Inboxes", href: "/inboxes" },
  {
    icon: <Workflow className="h-4 w-4" />,
    label: "Workflows",
    href: "/workflows",
    active: true, // default for example
  },
];

const FOOTER = [
  {
    icon: <FileText className="h-4 w-4" />,
    label: "Billing",
    href: "/billing",
  },
  { icon: <Users2 className="h-4 w-4" />, label: "Support", href: "/support" },
  {
    icon: <Settings className="h-4 w-4" />,
    label: "Integrations",
    href: "/integrations",
  },
];

export default function Sidebar() {
  const router = useRouter();

  const NavItem = ({
    icon,
    label,
    href,
    active,
  }: {
    icon: React.ReactNode;
    label: string;
    href: string;
    active?: boolean;
  }) => (
    <button
      onClick={() => router.push(href)}
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-muted text-indigo-600 dark:bg-gray-900"
          : "text-muted-foreground hover:bg-muted/70",
      )}
      aria-current={active ? "page" : undefined}
      type="button"
    >
      {icon}
      <span>{label}</span>
    </button>
  );

  return (
    <aside className="flex h-full w-56 flex-col border-r bg-white dark:bg-gray-950">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5">
        <Sparkle className="h-6 w-6 text-purple-600" />
        <span className="text-lg font-semibold">wrangle</span>
      </div>

      {/* Main nav */}
      <nav className="flex flex-col gap-1 px-2">
        {NAV.map((item) => (
          <NavItem key={item.label} {...item} />
        ))}
      </nav>

      {/* Footer */}
      <div className="mt-auto space-y-1 px-2 pb-4">
        {FOOTER.map((item) => (
          <NavItem key={item.label} {...item} />
        ))}
      </div>
    </aside>
  );
}
