import React from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  Workflow,
  FileText,
  Repeat,
  Layers,
  Paintbrush2,
  Users,
  Key,
  BookA,
  Puzzle,
  PackagePlus,
} from "lucide-react";

type ConfigStatus = "Required" | "Preferred" | "Optional";

const CONFIG_ITEMS: Array<{
  label: string;
  href: string;
  icon: React.ReactNode;
  desc: string;
  status: ConfigStatus;
  order?: number;
}> = [
  {
    label: "User Management",
    href: "/configuration/user-management",
    icon: <Users className="w-6 h-6 text-orange-500" />,
    desc: "Add, remove, and manage user accounts.",
    status: "Required",
    order: 2,
  },
  {
    label: "Permissions",
    href: "/configuration/permissions",
    icon: <Key className="w-6 h-6 text-yellow-500" />,
    desc: "Control access and roles for users.",
    status: "Required",
    order: 1,
  },
  {
    label: "Workflows",
    href: "/configuration/workflows",
    icon: <Workflow className="w-6 h-6 text-indigo-600" />,
    desc: "Set up and manage workflow templates.",
    status: "Required",
    order: 3,
  },
  {
    label: "Phases",
    href: "/configuration/phases",
    icon: <Repeat className="w-6 h-6 text-cyan-500" />,
    desc: "Customize workflow phases for document review.",
    status: "Required",
    order: 4,
  },
  {
    label: "Document Types",
    href: "/configuration/document-types",
    icon: <FileText className="w-6 h-6 text-blue-500" />,
    desc: "Define and edit document types used in projects.",
    status: "Required",
    order: 5,
  },
  {
    label: "Templates",
    href: "/configuration/templates",
    icon: <Layers className="w-6 h-6 text-violet-500" />,
    desc: "Maintain reusable content templates.",
    status: "Preferred",
  },
  {
    label: "Branding",
    href: "/configuration/branding",
    icon: <Paintbrush2 className="w-6 h-6 text-emerald-600" />,
    desc: "Customize company logo, product name, and footer links.",
    status: "Preferred",
  },
  {
    label: "Audit Logs",
    href: "/configuration/audit-logs",
    icon: <BookA className="w-6 h-6 text-lime-600" />,
    desc: "Review system activity and history.",
    status: "Optional",
  },
  {
    label: "Integrations",
    href: "/configuration/integrations",
    icon: <Puzzle className="w-6 h-6 text-pink-500" />,
    desc: "Connect with other tools and platforms.",
    status: "Optional",
  },
  {
    label: "Plugin Marketplace",
    href: "/configuration/plugin-marketplace",
    icon: <PackagePlus className="w-6 h-6 text-fuchsia-500" />,
    desc: "Browse and install optional plugins to extend functionality.",
    status: "Optional",
  },
];

const STATUS_STYLES: Record<ConfigStatus, { label: string; classes: string }> = {
  Required: {
    label: "Required",
    classes: "bg-red-50 text-red-700 border border-red-200",
  },
  Preferred: {
    label: "Preferred",
    classes: "bg-amber-50 text-amber-700 border border-amber-200",
  },
  Optional: {
    label: "Optional",
    classes: "bg-slate-50 text-slate-700 border border-slate-200",
  },
};

const CONFIG_GROUPS: Array<{
  title: string;
  description: string;
  status: ConfigStatus;
}> = [
  {
    title: "Required",
    description:
      "Suggested order: Permissions > Users > Workflows > Phases > Document Types. You can configure in any order, but this flow gets teams working fastest.",
    status: "Required",
  },
  {
    title: "Preferred",
    description: "Recommended next to standardize content and speed up teams.",
    status: "Preferred",
  },
  {
    title: "Optional",
    description: "Nice to have. Configure now or come back later based on need.",
    status: "Optional",
  },
];

export default function ConfigurationPage() {
  return (
    <div className="p-8 space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">Configuration</h1>
        <p className="text-sm text-gray-600 max-w-2xl">
          Start with the required items to get your workspace operational.
          Preferred settings improve consistency and speed, while optional items
          can be added anytime.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.values(STATUS_STYLES).map((status) => (
          <span
            key={status.label}
            className={`text-xs font-medium px-2 py-1 rounded-full ${status.classes}`}
          >
            {status.label}
          </span>
        ))}
      </div>

      {CONFIG_GROUPS.map((group) => {
        const items = CONFIG_ITEMS.filter((item) => item.status === group.status).sort((a, b) => {
          if (group.status !== "Required") {
            return 0;
          }

          return (a.order ?? 0) - (b.order ?? 0);
        });

        if (items.length === 0) {
          return null;
        }

        return (
          <section key={group.title} className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">{group.title}</h2>
              <p className="text-sm text-gray-500">{group.description}</p>
            </div>
            <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
              {items.map((item) => (
                <Link key={item.href} href={item.href} className="group">
                  <Card className="transition-shadow group-hover:shadow-lg h-full cursor-pointer">
                    <CardHeader className="flex flex-row items-start justify-between gap-3 pb-2">
                      <div className="flex items-center gap-3">
                        {item.icon}
                        <CardTitle className="text-lg font-semibold">{item.label}</CardTitle>
                      </div>
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded-full ${
                          STATUS_STYLES[item.status].classes
                        }`}
                      >
                        {STATUS_STYLES[item.status].label}
                      </span>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-gray-500">{item.desc}</p>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
