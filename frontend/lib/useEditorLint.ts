import { useState } from "react";

import type { ExtensionStatus } from "@/components/ExtensionsPanel";

interface UseEditorLintInput {
  persistPreferences: (overrides?: Partial<Record<string, boolean | string>>) => Promise<void>;
}

export function useEditorLint({ persistPreferences }: UseEditorLintInput) {
  const [lintEnabled, setLintEnabled] = useState(false);
  const [lintExtension, setLintExtension] = useState<any>(null);
  const [lintStatus, setLintStatus] = useState<ExtensionStatus>("idle");

  function handleToggleLint() {
    if (lintEnabled) {
      setLintEnabled(false);
      setLintExtension(null);
      setLintStatus("idle");
      void persistPreferences({ lint: false });
      return;
    }
    setLintStatus("loading");
    import("../extensions/lint")
      .then((mod) => {
        setLintExtension(() => mod.default);
        setLintEnabled(true);
        setLintStatus("loaded");
        void persistPreferences({ lint: true });
      })
      .catch(() => setLintStatus("error"));
  }

  return {
    lintEnabled,
    lintExtension,
    lintStatus,
    setLintEnabled,
    handleToggleLint,
  };
}
