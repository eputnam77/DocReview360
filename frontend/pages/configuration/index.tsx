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
  CheckCircle2,
  Settings2,
  Wrench,
} from "lucide-react";
import { useTranslation } from "@/lib/useTranslation";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ConfigStatus = "Required" | "Preferred" | "Optional";
type ConfigGroup = "Setup" | "Management" | "Advanced";

interface ConfigItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  desc: string;
  status: ConfigStatus;
  group: ConfigGroup;
  /** Sequential number within the Setup group to guide admins */
  step?: number;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ConfigurationPage() {
  const { t } = useTranslation();

  const CONFIG_ITEMS: ConfigItem[] = [
    // ---- Setup sequence (Required) ----------------------------------------
    {
      label: t("config.items.permissions.label", "Permissions"),
      href: "/configuration/permissions",
      icon: <Key className="w-6 h-6 text-yellow-500" />,
      desc: t("config.items.permissions.desc", "Control access and roles for users."),
      status: "Required",
      group: "Setup",
      step: 1,
    },
    {
      label: t("config.items.user_management.label", "User Management"),
      href: "/configuration/user-management",
      icon: <Users className="w-6 h-6 text-orange-500" />,
      desc: t("config.items.user_management.desc", "Add, remove, and manage user accounts."),
      status: "Required",
      group: "Setup",
      step: 2,
    },
    {
      label: t("config.items.workflows.label", "Workflows"),
      href: "/configuration/workflows",
      icon: <Workflow className="w-6 h-6 text-indigo-600" />,
      desc: t("config.items.workflows.desc", "Set up and manage workflow templates."),
      status: "Required",
      group: "Setup",
      step: 3,
    },
    {
      label: t("config.items.phases.label", "Phases"),
      href: "/configuration/phases",
      icon: <Repeat className="w-6 h-6 text-cyan-500" />,
      desc: t("config.items.phases.desc", "Customize workflow phases for document review."),
      status: "Required",
      group: "Setup",
      step: 4,
    },
    {
      label: t("config.items.document_types.label", "Document Types"),
      href: "/configuration/document-types",
      icon: <FileText className="w-6 h-6 text-blue-500" />,
      desc: t("config.items.document_types.desc", "Define and edit document types used in projects."),
      status: "Required",
      group: "Setup",
      step: 5,
    },
    // ---- Management (Preferred) --------------------------------------------
    {
      label: t("config.items.templates.label", "Templates"),
      href: "/configuration/templates",
      icon: <Layers className="w-6 h-6 text-violet-500" />,
      desc: t("config.items.templates.desc", "Maintain reusable content templates."),
      status: "Preferred",
      group: "Management",
    },
    {
      label: t("config.items.branding.label", "Branding"),
      href: "/configuration/branding",
      icon: <Paintbrush2 className="w-6 h-6 text-emerald-600" />,
      desc: t("config.items.branding.desc", "Customize company logo, product name, and footer links."),
      status: "Preferred",
      group: "Management",
    },
    // ---- Advanced (Optional) -----------------------------------------------
    {
      label: t("config.items.audit_logs.label", "Audit Logs"),
      href: "/configuration/audit-logs",
      icon: <BookA className="w-6 h-6 text-lime-600" />,
      desc: t("config.items.audit_logs.desc", "Review system activity and history."),
      status: "Optional",
      group: "Advanced",
    },
    {
      label: t("config.items.integrations.label", "Integrations"),
      href: "/configuration/integrations",
      icon: <Puzzle className="w-6 h-6 text-pink-500" />,
      desc: t("config.items.integrations.desc", "Connect with other tools and platforms."),
      status: "Optional",
      group: "Advanced",
    },
    {
      label: t("config.items.plugin_marketplace.label", "Plugin Marketplace"),
      href: "/configuration/plugin-marketplace",
      icon: <PackagePlus className="w-6 h-6 text-fuchsia-500" />,
      desc: t("config.items.plugin_marketplace.desc", "Browse and install optional plugins to extend functionality."),
      status: "Optional",
      group: "Advanced",
    },
  ];

  const STATUS_STYLES: Record<ConfigStatus, { label: string; classes: string }> = {
    Required: {
      label: t("config.status.required", "Required"),
      classes: "bg-red-50 text-red-700 border border-red-200",
    },
    Preferred: {
      label: t("config.status.preferred", "Preferred"),
      classes: "bg-amber-50 text-amber-700 border border-amber-200",
    },
    Optional: {
      label: t("config.status.optional", "Optional"),
      classes: "bg-slate-50 text-slate-700 border border-slate-200",
    },
  };

  const GROUP_META: Array<{
    group: ConfigGroup;
    title: string;
    description: string;
    groupIcon: React.ReactNode;
    accentClasses: string;
  }> = [
    {
      group: "Setup",
      title: t("config.group.setup.title", "Setup"),
      description: t(
        "config.group.setup.desc",
        "Complete these steps in order to get your workspace operational. Follow the sequence numbers for the fastest path to a working environment.",
      ),
      groupIcon: <CheckCircle2 className="w-5 h-5 text-red-600" />,
      accentClasses: "border-l-4 border-red-400 pl-4",
    },
    {
      group: "Management",
      title: t("config.group.management.title", "Management"),
      description: t(
        "config.group.management.desc",
        "Recommended once the workspace is running. These settings standardize content and help teams work faster.",
      ),
      groupIcon: <Settings2 className="w-5 h-5 text-amber-600" />,
      accentClasses: "border-l-4 border-amber-400 pl-4",
    },
    {
      group: "Advanced",
      title: t("config.group.advanced.title", "Advanced"),
      description: t(
        "config.group.advanced.desc",
        "Optional capabilities — connect external tools, review audit history, or extend functionality with plugins. Configure at any time.",
      ),
      groupIcon: <Wrench className="w-5 h-5 text-slate-500" />,
      accentClasses: "border-l-4 border-slate-300 pl-4",
    },
  ];

  return (
    <div className="p-8 space-y-10">
      {/* Page header */}
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">{t("config.title", "Configuration")}</h1>
        <p className="text-sm text-gray-600 max-w-2xl">
          {t(
            "config.intro",
            "Start with the Setup sequence to get your workspace operational. Move to Management settings to standardize content, then explore Advanced capabilities as needed.",
          )}
        </p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-xs text-gray-500 mr-1">{t("config.legend", "Status:")}</span>
        {Object.values(STATUS_STYLES).map((s) => (
          <span
            key={s.label}
            className={`text-xs font-medium px-2 py-1 rounded-full ${s.classes}`}
          >
            {s.label}
          </span>
        ))}
      </div>

      {/* Groups */}
      {GROUP_META.map(({ group, title, description, groupIcon, accentClasses }) => {
        const items = CONFIG_ITEMS.filter((item) => item.group === group).sort(
          (a, b) => (a.step ?? 99) - (b.step ?? 99),
        );

        if (items.length === 0) return null;

        return (
          <section key={group} className="space-y-4">
            {/* Group header */}
            <div className={accentClasses}>
              <div className="flex items-center gap-2">
                {groupIcon}
                <h2 className="text-lg font-semibold">{title}</h2>
              </div>
              <p className="text-sm text-gray-500 mt-0.5">{description}</p>
            </div>

            {/* Item grid */}
            <div className="grid gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
              {items.map((item) => (
                <Link key={item.href} href={item.href} className="group">
                  <Card className="transition-shadow group-hover:shadow-lg h-full cursor-pointer">
                    <CardHeader className="flex flex-row items-start justify-between gap-3 pb-2">
                      <div className="flex items-center gap-3">
                        {/* Sequence number badge for Setup group */}
                        {item.step != null ? (
                          <div className="relative flex-shrink-0">
                            {item.icon}
                            <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-white text-[9px] font-bold leading-none">
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
