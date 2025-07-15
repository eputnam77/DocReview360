// frontend/components/workflow/Sidebar.tsx

import React from "react";
import { useRouter } from "next/navigation";
import {
  Sparkle,
  Ticket,
  Inbox,
  Users2,
  Settings,
  User,
  Workflow,
  FileText,
  Repeat,
  Layers,
  Users,
  Key,
  BookA,
  Settings2,
  Puzzle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUserStore } from "@/state/user";

const NAV = [
  { icon: <Ticket className="h-4 w-4" />, label: "Projects", href: "/projects" },
  { icon: <Inbox className="h-4 w-4" />, label: "Dashboard", href: "/dashboard" },
];

const SECONDARY = [
  {
    icon: <Users2 className="h-4 w-4" />,
    label: "Support",
    href: "/docs/",
  },
  {
    icon: <Inbox className="h-4 w-4" />,
    label: "Logs",
    href: "/logs",
  },
];

const CONFIG = [
  {
    icon: <Workflow className="h-4 w-4" />,
    label: "Workflows",
    href: "/configuration/workflows",
  },
  {
    icon: <FileText className="h-4 w-4" />,
    label: "Document Types",
    href: "/configuration/document-types",
  },
  {
    icon: <Repeat className="h-4 w-4" />,
    label: "Phases",
    href: "/configuration/phases",
  },
  {
    icon: <Layers className="h-4 w-4" />,
    label: "Templates",
    href: "/configuration/templates",
  },
  {
    icon: <Users className="h-4 w-4" />,
    label: "User Management",
    href: "/configuration/user-management",
  },
  {
    icon: <Key className="h-4 w-4" />,
    label: "Permissions",
    href: "/configuration/permissions",
  },
  {
    icon: <BookA className="h-4 w-4" />,
    label: "Audit Logs",
    href: "/configuration/audit-logs",
  },
  {
    icon: <Settings2 className="h-4 w-4" />,
    label: "App Settings",
    href: "/configuration/app-settings",
  },
  {
    icon: <Puzzle className="h-4 w-4" />,
    label: "Integrations",
    href: "/configuration/integrations",
  },
];

const PROFILE = { icon: <User className="h-4 w-4" />, label: "Profile", href: "/profile" };

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

  const isAdmin = useUserStore((s) => s.isAdmin);

  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-white dark:bg-gray-950">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5">
        <Sparkle className="h-6 w-6 text-purple-600" />
        {/* Replace text with organization logo if available */}
        <span className="text-lg font-semibold">DocReview360</span>
      </div>

      {/* Main nav */}
      <nav className="flex flex-col gap-1 px-2">
        {NAV.map((item) => (
          <NavItem key={item.label} {...item} />
        ))}
      </nav>

      <hr className="my-4" />

      {/* Secondary */}
      <div className="space-y-1 px-2">
        {SECONDARY.map((item) => (
          <NavItem key={item.label} {...item} />
        ))}
      </div>

      <hr className="my-4" />

      <div className="px-2">
        <NavItem {...PROFILE} />
      </div>

      {isAdmin && (
        <>
          <hr className="my-4" />
          <div className="px-2 space-y-1">
            <div className="flex items-center gap-2 px-3 py-2 text-xs font-semibold uppercase text-muted-foreground">
              <Settings className="h-4 w-4" />
              <span>Configuration</span>
            </div>
            {CONFIG.map((item) => (
              <NavItem key={item.label} {...item} />
            ))}
          </div>
        </>
      )}

    </aside>
  );
}
