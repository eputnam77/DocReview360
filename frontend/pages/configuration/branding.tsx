import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authenticatedFetch } from "@/lib/api";
import { useBrandingStore } from "@/state/branding";

const MAX_LOGO_BYTES = 256 * 1024;
const ALLOWED_LOGO_TYPES = ["image/png", "image/jpeg", "image/webp", "image/svg+xml"];
const DEFAULT_ORG_ID = "system";

type ConfigPayload = Record<string, unknown>;

interface OrgThemeColors {
  primary_color: string;
  accent_color: string;
  sidebar_bg: string;
  sidebar_text: string;
}

export default function BrandingConfigurationPage() {
  const [config, setConfig] = useState<ConfigPayload | null>(null);
  const [companyName, setCompanyName] = useState("DocReview360");
  const [logoUrl, setLogoUrl] = useState("");
  const [logoAlt, setLogoAlt] = useState("Organization logo");
  const [supportUrl, setSupportUrl] = useState("/docs/");
  const [docsUrl, setDocsUrl] = useState("/docs/");
  const [securityUrl, setSecurityUrl] = useState("/security");
  const [privacyUrl, setPrivacyUrl] = useState("/privacy");
  const [isSaving, setIsSaving] = useState(false);

  // Theme color state (org-level branding API)
  const [primaryColor, setPrimaryColor] = useState("#2563eb");
  const [accentColor, setAccentColor] = useState("#16a34a");
  const [sidebarBg, setSidebarBg] = useState("#ffffff");
  const [sidebarText, setSidebarText] = useState("#111827");
  const [isSavingTheme, setIsSavingTheme] = useState(false);

  const refreshBranding = useBrandingStore((s) => s.initialize);

  useEffect(() => {
    void (async () => {
      try {
        const resp = await authenticatedFetch("/config");
        if (!resp.ok) {
          throw new Error(await resp.text());
        }
        const data = (await resp.json()) as ConfigPayload;
        setConfig(data);
        setCompanyName(String(data.branding_company_name ?? "DocReview360"));
        setLogoUrl(String(data.branding_logo_url ?? ""));
        setLogoAlt(String(data.branding_logo_alt ?? "Organization logo"));
        setSupportUrl(String(data.branding_support_url ?? "/docs/"));
        setDocsUrl(String(data.branding_docs_url ?? "/docs/"));
        setSecurityUrl(String(data.branding_security_url ?? "/security"));
        setPrivacyUrl(String(data.branding_privacy_url ?? "/privacy"));
      } catch (error) {
        console.error("Failed to load branding configuration", error);
        toast.error("Failed to load branding settings.");
      }
    })();

    // Load org-level theme colors.
    void (async () => {
      try {
        const resp = await authenticatedFetch(`/orgs/${DEFAULT_ORG_ID}/branding`);
        if (!resp.ok) return;
        const data = (await resp.json()) as { branding?: OrgThemeColors };
        const b = data.branding;
        if (b) {
          if (b.primary_color) setPrimaryColor(b.primary_color);
          if (b.accent_color) setAccentColor(b.accent_color);
          if (b.sidebar_bg) setSidebarBg(b.sidebar_bg);
          if (b.sidebar_text) setSidebarText(b.sidebar_text);
        }
      } catch {
        // Org branding endpoint may not exist yet; silently ignore.
      }
    })();
  }, []);

  const hasLogo = useMemo(() => logoUrl.trim().length > 0, [logoUrl]);

  const handleFileUpload = async (file: File | null | undefined) => {
    if (!file) {
      return;
    }
    if (!ALLOWED_LOGO_TYPES.includes(file.type)) {
      toast.error("Logo file type must be PNG, JPEG, WEBP, or SVG.");
      return;
    }
    if (file.size > MAX_LOGO_BYTES) {
      toast.error("Logo file exceeds 256 KB limit.");
      return;
    }

    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === "string") {
          resolve(reader.result);
          return;
        }
        reject(new Error("Unable to read image file"));
      };
      reader.onerror = () => reject(new Error("Unable to read image file"));
      reader.readAsDataURL(file);
    });

    setLogoUrl(dataUrl);
    if (!logoAlt.trim()) {
      setLogoAlt("Organization logo");
    }
    toast.success("Logo uploaded. Save to apply branding.");
  };

  const handleSave = async () => {
    if (!config) {
      toast.error("Configuration is not loaded yet.");
      return;
    }
    if (!companyName.trim()) {
      toast.error("Company name is required.");
      return;
    }
    if (hasLogo && !logoAlt.trim()) {
      toast.error("Logo alt text is required when a logo is configured.");
      return;
    }

    const payload: ConfigPayload = {
      ...config,
      branding_company_name: companyName.trim(),
      branding_logo_url: logoUrl.trim() || null,
      branding_logo_alt: logoAlt.trim() || "Organization logo",
      branding_support_url: supportUrl.trim() || "/docs/",
      branding_docs_url: docsUrl.trim() || "/docs/",
      branding_security_url: securityUrl.trim() || "/security",
      branding_privacy_url: privacyUrl.trim() || "/privacy",
    };

    setIsSaving(true);
    try {
      const resp = await authenticatedFetch("/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        throw new Error(await resp.text());
      }
      const saved = (await resp.json()) as ConfigPayload;
      setConfig(saved);
      await refreshBranding(true);
      toast.success("Branding settings saved.");
    } catch (error) {
      console.error("Failed to save branding configuration", error);
      toast.error("Failed to save branding settings.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveTheme = async () => {
    setIsSavingTheme(true);
    try {
      const resp = await authenticatedFetch(`/orgs/${DEFAULT_ORG_ID}/branding`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          primary_color: primaryColor || null,
          accent_color: accentColor || null,
          sidebar_bg: sidebarBg || null,
          sidebar_text: sidebarText || null,
        }),
      });
      if (!resp.ok) {
        throw new Error(await resp.text());
      }
      await refreshBranding(true);
      toast.success("Theme colors saved.");
    } catch (error) {
      console.error("Failed to save theme colors", error);
      toast.error("Failed to save theme colors.");
    } finally {
      setIsSavingTheme(false);
    }
  };

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="text-2xl font-bold">Branding</h1>
        <p className="mt-1 text-sm text-gray-500">
          Replace the default DocReview360 mark with your company name and logo.
          Guardrails enforce image type/size limits and safe fallback behavior.
        </p>
      </div>

      <div className="grid max-w-2xl gap-4">
        <div className="space-y-2">
          <Label htmlFor="company-name">Company Name</Label>
          <Input
            id="company-name"
            value={companyName}
            onChange={(event) => setCompanyName(event.target.value)}
            placeholder="Acme Aviation"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="logo-url">Logo URL or Data URL</Label>
          <Input
            id="logo-url"
            value={logoUrl}
            onChange={(event) => setLogoUrl(event.target.value)}
            placeholder="https://example.com/logo.png"
          />
          <p className="text-xs text-gray-500">
            Allowed URL extensions: .png, .jpg, .jpeg, .webp, .svg
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="logo-file">Upload Logo (Optional)</Label>
          <Input
            id="logo-file"
            type="file"
            accept={ALLOWED_LOGO_TYPES.join(",")}
            onChange={(event) => {
              const file = event.target.files?.item(0);
              void handleFileUpload(file);
            }}
          />
          <p className="text-xs text-gray-500">Max size: 256 KB.</p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="logo-alt">Logo Alt Text</Label>
          <Input
            id="logo-alt"
            value={logoAlt}
            onChange={(event) => setLogoAlt(event.target.value)}
            placeholder="Acme Aviation logo"
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="support-url">Support Link</Label>
            <Input
              id="support-url"
              value={supportUrl}
              onChange={(event) => setSupportUrl(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="docs-url">Docs Link</Label>
            <Input
              id="docs-url"
              value={docsUrl}
              onChange={(event) => setDocsUrl(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="security-url">Security Link</Label>
            <Input
              id="security-url"
              value={securityUrl}
              onChange={(event) => setSecurityUrl(event.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="privacy-url">Privacy Link</Label>
            <Input
              id="privacy-url"
              value={privacyUrl}
              onChange={(event) => setPrivacyUrl(event.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          <Button onClick={handleSave} disabled={isSaving || !config}>
            {isSaving ? "Saving..." : "Save Branding"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setLogoUrl("");
              setLogoAlt("Organization logo");
            }}
          >
            Clear Logo
          </Button>
        </div>
      </div>

      {/* Theme Colors section */}
      <div>
        <h2 className="text-lg font-semibold">Theme Colors</h2>
        <p className="mt-1 text-sm text-gray-500">
          Customize the primary action color, accent color, and sidebar appearance for your
          organization. Values must be CSS hex colors (e.g.{" "}
          <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">#6366f1</code>).
        </p>
      </div>

      <div className="grid max-w-2xl gap-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="primary-color">Primary Color</Label>
            <div className="flex items-center gap-2">
              <input
                id="primary-color-swatch"
                type="color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="h-9 w-14 cursor-pointer rounded border border-input p-0.5"
                aria-label="Primary color picker"
              />
              <Input
                id="primary-color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                placeholder="#2563eb"
                className="font-mono"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="accent-color">Accent Color</Label>
            <div className="flex items-center gap-2">
              <input
                id="accent-color-swatch"
                type="color"
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
                className="h-9 w-14 cursor-pointer rounded border border-input p-0.5"
                aria-label="Accent color picker"
              />
              <Input
                id="accent-color"
                value={accentColor}
                onChange={(e) => setAccentColor(e.target.value)}
                placeholder="#16a34a"
                className="font-mono"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="sidebar-bg">Sidebar Background</Label>
            <div className="flex items-center gap-2">
              <input
                id="sidebar-bg-swatch"
                type="color"
                value={sidebarBg}
                onChange={(e) => setSidebarBg(e.target.value)}
                className="h-9 w-14 cursor-pointer rounded border border-input p-0.5"
                aria-label="Sidebar background color picker"
              />
              <Input
                id="sidebar-bg"
                value={sidebarBg}
                onChange={(e) => setSidebarBg(e.target.value)}
                placeholder="#1e293b"
                className="font-mono"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="sidebar-text">Sidebar Text</Label>
            <div className="flex items-center gap-2">
              <input
                id="sidebar-text-swatch"
                type="color"
                value={sidebarText}
                onChange={(e) => setSidebarText(e.target.value)}
                className="h-9 w-14 cursor-pointer rounded border border-input p-0.5"
                aria-label="Sidebar text color picker"
              />
              <Input
                id="sidebar-text"
                value={sidebarText}
                onChange={(e) => setSidebarText(e.target.value)}
                placeholder="#f8fafc"
                className="font-mono"
              />
            </div>
          </div>
        </div>

        {/* Live preview swatch */}
        <div
          className="flex h-14 w-full items-center gap-4 rounded-md border px-4 text-sm font-medium shadow-inner"
          style={{ backgroundColor: sidebarBg, color: sidebarText }}
          aria-label="Sidebar theme preview"
        >
          <span
            className="rounded px-3 py-1 text-white"
            style={{ backgroundColor: primaryColor }}
          >
            Primary
          </span>
          <span
            className="rounded px-3 py-1 text-white"
            style={{ backgroundColor: accentColor }}
          >
            Accent
          </span>
          <span className="ml-auto">Preview</span>
        </div>

        <div className="flex gap-2 pt-2">
          <Button onClick={handleSaveTheme} disabled={isSavingTheme}>
            {isSavingTheme ? "Saving..." : "Save Theme Colors"}
          </Button>
        </div>
      </div>
    </div>
  );
}
