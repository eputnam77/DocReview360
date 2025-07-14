import React from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
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

// List of configuration sections
const CONFIG_ITEMS = [
  {
    label: "Workflows",
    href: "/configuration/workflows",
    icon: <Workflow className="w-6 h-6 text-indigo-600" />,
    desc: "Set up and manage workflow templates."
  },
  {
    label: "Document Types",
    href: "/configuration/document-types",
    icon: <FileText className="w-6 h-6 text-blue-500" />,
    desc: "Define and edit document types used in projects."
  },
  {
    label: "Phases",
    href: "/configuration/phases",
    icon: <Repeat className="w-6 h-6 text-cyan-500" />,
    desc: "Customize workflow phases for document review."
  },
  {
    label: "Templates",
    href: "/configuration/templates",
    icon: <Layers className="w-6 h-6 text-violet-500" />,
    desc: "Maintain reusable content templates."
  },
  {
    label: "User Management",
    href: "/configuration/user-management",
    icon: <Users className="w-6 h-6 text-orange-500" />,
    desc: "Add, remove, and manage user accounts."
  },
  {
    label: "Permissions",
    href: "/configuration/permissions",
    icon: <Key className="w-6 h-6 text-yellow-500" />,
    desc: "Control access and roles for users."
  },
  {
    label: "Audit Logs",
    href: "/configuration/audit-logs",
    icon: <BookA className="w-6 h-6 text-lime-600" />,
    desc: "Review system activity and history."
  },
  {
    label: "App Settings",
    href: "/configuration/app-settings",
    icon: <Settings2 className="w-6 h-6 text-gray-600" />,
    desc: "Configure global app preferences."
  },
  {
    label: "Integrations",
    href: "/configuration/integrations",
    icon: <Puzzle className="w-6 h-6 text-pink-500" />,
    desc: "Connect with other tools and platforms."
  },
];

export default function ConfigurationPage() {
  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Configuration</h1>
      <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
        {CONFIG_ITEMS.map((item) => (
          <Link key={item.href} href={item.href} className="group">
            <Card className="transition-shadow group-hover:shadow-lg h-full cursor-pointer">
              <CardHeader className="flex flex-row items-center gap-3 pb-2">
                {item.icon}
                <CardTitle className="text-lg font-semibold">
                  {item.label}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-500">{item.desc}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
