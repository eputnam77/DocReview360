// frontend/components/workflow/Sidebar.tsx

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Sparkle,
  Ticket,
  Inbox,
  Users2,
  Settings,
  User,
  Wrench,
  LogIn,
  LogOut,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useBrandingStore } from "@/state/branding";
import { useUserStore } from "@/state/user";
import SearchBar from "../SearchBar";
import EnvironmentSwitcher from "../EnvironmentSwitcher";

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
    icon: <Wrench className="h-4 w-4" />,
    label: "Tools",
    href: "/tools",
  },
];

const PROFILE = { icon: <User className="h-4 w-4" />, label: "Profile", href: "/profile" };

export default function Sidebar() {
  const router = useRouter();
  const [logoFailed, setLogoFailed] = useState(false);

  const initializeBranding = useBrandingStore((s) => s.initialize);
  const brandingCompanyName = useBrandingStore((s) => s.brandingCompanyName);
  const brandingLogoUrl = useBrandingStore((s) => s.brandingLogoUrl);
  const brandingLogoAlt = useBrandingStore((s) => s.brandingLogoAlt);

  useEffect(() => {
    void initializeBranding();
  }, [initializeBranding]);

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
  const logout = useUserStore((s) => s.logout);

  const showLogo = Boolean(brandingLogoUrl) && !logoFailed;

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-border bg-background text-foreground">
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

      <div className="mt-auto border-t border-border p-2">
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
