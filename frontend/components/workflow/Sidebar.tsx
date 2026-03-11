// frontend/components/workflow/Sidebar.tsx

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkle,
  Ticket,
  Inbox,
  Settings,
  User,
  Wrench,
  LogIn,
  LogOut,
  HelpCircle,
  BookOpen,
  Rocket,
  Keyboard,
  Code2,
  Info,
  Phone,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useTheme } from "@/lib/useTheme";
import { useBrandingStore } from "@/state/branding";
import { useUserStore } from "@/state/user";
import SearchBar from "../SearchBar";
import EnvironmentSwitcher from "../EnvironmentSwitcher";
import LocaleSwitcher from "@/components/LocaleSwitcher";

const STATIC_NAV = [
  { icon: <Ticket className="h-4 w-4" />, label: "Projects", href: "/projects" },
];

const SECONDARY = [
  {
    icon: <Wrench className="h-4 w-4" />,
    label: "Tools",
    href: "/tools",
  },
];

const PROFILE = { icon: <User className="h-4 w-4" />, label: "Profile", href: "/profile" };

// Defaults matching the branding store defaults.
const DEFAULT_DOCS_URL = "/docs/";
const DEFAULT_SUPPORT_URL = "/docs/";

export default function Sidebar() {
  const router = useRouter();
  const [logoFailed, setLogoFailed] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  // Inject theme CSS custom properties into :root whenever branding colors change.
  useTheme();

  const initializeBranding = useBrandingStore((s) => s.initialize);
  const brandingCompanyName = useBrandingStore((s) => s.brandingCompanyName);
  const brandingLogoUrl = useBrandingStore((s) => s.brandingLogoUrl);
  const brandingLogoAlt = useBrandingStore((s) => s.brandingLogoAlt);
  const brandingDocsUrl = useBrandingStore((s) => s.brandingDocsUrl);
  const brandingSupportUrl = useBrandingStore((s) => s.brandingSupportUrl);

  useEffect(() => {
    void initializeBranding();
  }, [initializeBranding]);

  // Use org-configured docs URL when it differs from the default placeholder,
  // otherwise fall through to the in-app help page.
  const docsUrl =
    brandingDocsUrl && brandingDocsUrl !== DEFAULT_DOCS_URL ? brandingDocsUrl : "/help";

  // Only surface "Contact Support" when an org has configured a real URL.
  const supportUrl =
    brandingSupportUrl && brandingSupportUrl !== DEFAULT_SUPPORT_URL
      ? brandingSupportUrl
      : null;

  const NavItem = ({
    icon,
    label,
    href,
    active,
    external,
  }: {
    icon: React.ReactNode;
    label: string;
    href: string;
    active?: boolean;
    external?: boolean;
  }) => (
    <button
      onClick={() => {
        if (external) {
          window.open(href, "_blank", "noopener,noreferrer");
        } else {
          router.push(href);
        }
      }}
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-muted text-indigo-600 dark:bg-gray-900 dark:text-indigo-300"
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
  const username = useUserStore((s) => s.username);
  const roles = useUserStore((s) => s.roles);
  const logout = useUserStore((s) => s.logout);

  const dashboardNav = isAdmin
    ? { icon: <Inbox className="h-4 w-4" />, label: "Admin Dashboard", href: "/dashboard/admin" }
    : roles.includes("manager")
      ? { icon: <Inbox className="h-4 w-4" />, label: "Manager Dashboard", href: "/dashboard/manager" }
      : { icon: <Inbox className="h-4 w-4" />, label: "My Dashboard", href: "/dashboard/user" };

  const NAV = [...STATIC_NAV, dashboardNav];

  const showLogo = Boolean(brandingLogoUrl) && !logoFailed;

  return (
    <aside
      className="flex h-screen w-56 flex-col border-r border-border bg-background text-foreground"
      style={{ backgroundColor: "var(--sidebar-bg, inherit)", color: "var(--sidebar-text, inherit)" }}
    >
      <div className="flex items-center gap-2 px-4 py-5">
        {showLogo ? (
          <img
            src={brandingLogoUrl ?? undefined}
            alt={brandingLogoAlt || "Organization logo"}
            className="h-6 w-6 rounded object-contain"
            onError={() => setLogoFailed(true)}
          />
        ) : (
          <Sparkle className="h-6 w-6 text-purple-600" />
        )}
        <span className="truncate text-lg font-semibold">
          {brandingCompanyName || "DocReview360"}
        </span>
      </div>

      <div className="px-4 pb-4">
        <EnvironmentSwitcher />
      </div>

      <SearchBar />

      <nav className="flex flex-col gap-1 px-2">
        {NAV.map((item) => (
          <NavItem key={item.label} {...item} />
        ))}
      </nav>

      <hr className="my-4 border-border" />

      <div className="space-y-1 px-2">
        {SECONDARY.map((item) => (
          <NavItem key={item.label} {...item} />
        ))}

        {/* Collapsible Help & Support section */}
        <button
          type="button"
          onClick={() => setHelpOpen((v) => !v)}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/70"
          aria-expanded={helpOpen}
        >
          <HelpCircle className="h-4 w-4" />
          <span className="flex-1 text-left">Help &amp; Support</span>
          {helpOpen ? (
            <ChevronUp className="h-3 w-3 flex-shrink-0" />
          ) : (
            <ChevronDown className="h-3 w-3 flex-shrink-0" />
          )}
        </button>

        {helpOpen && (
          <div className="ml-4 mt-0.5 space-y-0.5 border-l border-border pl-2">
            <NavItem
              icon={<BookOpen className="h-4 w-4" />}
              label="Documentation"
              href={docsUrl}
              external={docsUrl.startsWith("http")}
            />
            <NavItem
              icon={<Rocket className="h-4 w-4" />}
              label="Getting Started"
              href="/help#getting-started"
            />
            <NavItem
              icon={<Keyboard className="h-4 w-4" />}
              label="Keyboard Shortcuts"
              href="/help#shortcuts"
            />
            <NavItem
              icon={<Code2 className="h-4 w-4" />}
              label="API Reference"
              href="/api-docs"
            />
            <NavItem
              icon={<Info className="h-4 w-4" />}
              label="About"
              href="/about"
            />
            {supportUrl && (
              <NavItem
                icon={<Phone className="h-4 w-4" />}
                label="Contact Support"
                href={supportUrl}
                external={supportUrl.startsWith("http")}
              />
            )}
          </div>
        )}
      </div>

      <hr className="my-4 border-border" />

      <div className="px-2">
        <NavItem {...PROFILE} />
      </div>

      {isAdmin && (
        <>
          <hr className="my-4 border-border" />
          <div className="px-2">
            <NavItem
              icon={<Settings className="h-4 w-4" />}
              label="Configuration"
              href="/configuration"
            />
          </div>
        </>
      )}

      <div className="mt-auto border-t border-border p-2 space-y-2">
        <div className="px-3 py-1">
          <LocaleSwitcher />
        </div>
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/70"
          onClick={async () => {
            if (username) {
              await logout();
            }
            router.push("/login");
          }}
        >
          {username ? <LogOut className="h-4 w-4" /> : <LogIn className="h-4 w-4" />}
          <span>{username ? "Log off" : "Log in"}</span>
        </button>
      </div>
    </aside>
  );
}
