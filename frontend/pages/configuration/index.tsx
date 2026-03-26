import React from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
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
  CheckCircle2,
  Settings2,
  Wrench,
  Shield,
  Globe,
} from "lucide-react";
import { useTranslation } from "@/lib/useTranslation";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ConfigStatus = "Required" | "Preferred" | "Optional";

interface ConfigItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  desc: string;
  status: ConfigStatus;
  step?: number;
}

// ---------------------------------------------------------------------------
// Setup sequence groups (mirrors Help page structure)
// ---------------------------------------------------------------------------

const SETUP_SECTIONS: Array<{
  value: string;
  label: string;
  icon: React.ReactNode;
  description: string;
  items: ConfigItem[];
}> = [
  {
    value: "basic-setup",
    label: "Basic Setup",
    icon: <CheckCircle2 className="w-4 h-4 mr-1.5" />,
    description:
      "Complete these steps first to make your workspace operational. Follow the numbered sequence for the fastest path.",
    items: [
      {
        label: "Permissions",
        href: "/configuration/permissions",
        icon: <Key className="w-6 h-6 text-yellow-500" />,
        desc: "Control access and roles for users.",
        status: "Required",
        step: 1,
      },
      {
        label: "User Management",
        href: "/configuration/user-management",
        icon: <Users className="w-6 h-6 text-orange-500" />,
        desc: "Add, remove, and manage user accounts.",
        status: "Required",
        step: 2,
      },
    ],
  },
  {
    value: "users-permissions",
    label: "Users & Permissions",
    icon: <Shield className="w-4 h-4 mr-1.5" />,
    description:
      "Fine-tune access control, roles, and team membership after the initial setup.",
    items: [
      {
        label: "Permissions",
        href: "/configuration/permissions",
        icon: <Key className="w-6 h-6 text-yellow-500" />,
        desc: "Configure role-based access control and permission sets.",
        status: "Required",
      },
      {
        label: "User Management",
        href: "/configuration/user-management",
        icon: <Users className="w-6 h-6 text-orange-500" />,
        desc: "Manage team members, invite new users, and deactivate accounts.",
        status: "Required",
      },
    ],
  },
  {
    value: "workflows-doctypes",
    label: "Workflows & Document Types",
    icon: <Workflow className="w-4 h-4 mr-1.5" />,
    description:
      "Define the lifecycle each document must follow and the types of documents your team reviews.",
    items: [
      {
        label: "Workflows",
        href: "/configuration/workflows",
        icon: <Workflow className="w-6 h-6 text-indigo-600" />,
        desc: "Create and manage workflow templates that define review phases.",
        status: "Required",
        step: 1,
      },
      {
        label: "Phases",
        href: "/configuration/phases",
        icon: <Repeat className="w-6 h-6 text-cyan-500" />,
        desc: "Customize workflow phases — for example Draft, Review, Approval, Final.",
        status: "Required",
        step: 2,
      },
      {
        label: "Document Types",
        href: "/configuration/document-types",
        icon: <FileText className="w-6 h-6 text-blue-500" />,
        desc: "Define document categories that determine which workflow applies.",
        status: "Required",
        step: 3,
      },
      {
        label: "Templates",
        href: "/configuration/templates",
        icon: <Layers className="w-6 h-6 text-violet-500" />,
        desc: "Maintain reusable content and document templates.",
        status: "Preferred",
      },
    ],
  },
  {
    value: "integrations",
    label: "Integrations",
    icon: <Globe className="w-4 h-4 mr-1.5" />,
    description:
      "Connect DocReview360 to external signature providers, notification services, and other tools.",
    items: [
      {
        label: "Integrations",
        href: "/configuration/integrations",
        icon: <Puzzle className="w-6 h-6 text-pink-500" />,
        desc: "Connect with Documenso, DocuSign, and other platforms.",
        status: "Optional",
      },
      {
        label: "Plugin Marketplace",
        href: "/configuration/plugin-marketplace",
        icon: <PackagePlus className="w-6 h-6 text-fuchsia-500" />,
        desc: "Browse and install optional plugins to extend functionality.",
        status: "Optional",
      },
    ],
  },
  {
    value: "advanced",
    label: "Advanced",
    icon: <Wrench className="w-4 h-4 mr-1.5" />,
    description:
      "Branding customisation, audit history, and other advanced configuration — set up at any time.",
    items: [
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
    ],
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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ConfigurationPage() {
  const { t } = useTranslation();

  return (
    <div className="p-8 space-y-6 max-w-5xl">
      {/* Page header — same structure as Help page */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings2 className="w-6 h-6 text-indigo-600" />
          {t("config.title", "Configuration")}
        </h1>
        <p className="text-sm text-muted-foreground">
          {t(
            "config.intro",
            "Set up your workspace using the tabs below. Start with Basic Setup, then configure Workflows and Document Types before exploring Integrations and Advanced options.",
          )}
        </p>
      </div>

      {/* Status legend */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-muted-foreground mr-1">{t("config.legend", "Status:")}</span>
        {Object.values(STATUS_STYLES).map((s) => (
          <span
            key={s.label}
            className={`text-xs font-medium px-2 py-1 rounded-full ${s.classes}`}
          >
            {s.label}
          </span>
        ))}
      </div>

      {/* Tab-based sections — mirrors the Help page structure */}
      <Tabs defaultValue="basic-setup">
        <TabsList className="flex-wrap h-auto">
          {SETUP_SECTIONS.map((section) => (
            <TabsTrigger key={section.value} value={section.value}>
              {section.icon}
              {section.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {SETUP_SECTIONS.map((section) => (
          <TabsContent key={section.value} value={section.value} className="mt-6 space-y-4">
            <p className="text-sm text-muted-foreground">{section.description}</p>

            <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3">
              {section.items.map((item) => (
                <Link key={item.href + item.label} href={item.href} className="group">
                  <Card className="h-full transition-shadow group-hover:shadow-md cursor-pointer">
                    <CardHeader className="flex flex-row items-start justify-between gap-3 pb-2">
                      <div className="flex items-center gap-3">
                        {/* Sequence number badge for stepped items */}
                        {item.step != null ? (
                          <div className="relative flex-shrink-0">
                            {item.icon}
                            <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 text-white text-[9px] font-bold leading-none">
                              {item.step}
                            </span>
                          </div>
                        ) : (
                          item.icon
                        )}
                        <CardTitle className="text-base font-semibold leading-snug">
                          {item.label}
                        </CardTitle>
                      </div>
                      <span
                        className={`flex-shrink-0 text-xs font-medium px-2 py-1 rounded-full ${
                          STATUS_STYLES[item.status].classes
                        }`}
                      >
                        {STATUS_STYLES[item.status].label}
                      </span>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">{item.desc}</p>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
