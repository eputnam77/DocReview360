import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authenticatedFetch } from "@/lib/api";
import { useBrandingStore } from "@/state/branding";

const MAX_LOGO_BYTES = 256 * 1024;
const ALLOWED_LOGO_TYPES = ["image/png", "image/jpeg", "image/webp", "image/svg+xml"];

type ConfigPayload = Record<string, unknown>;

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
    </div>
  );
}
