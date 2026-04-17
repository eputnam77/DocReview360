import { useState } from "react";

import * as Y from "yjs";

interface UseEditorCollabInput {
  persistPreferences: (overrides?: Partial<Record<string, boolean | string>>) => Promise<void>;
}

export function useEditorCollab({ persistPreferences }: UseEditorCollabInput) {
  const [collabEnabled, setCollabEnabled] = useState(false);
  const [yDoc, setYDoc] = useState<Y.Doc | null>(null);
  const [provider, setProvider] = useState<any>(null);

  function handleToggleCollab() {
    setCollabEnabled((prev) => {
      const next = !prev;
      if (prev && provider) {
        provider.disconnect();
        setYDoc(null);
        setProvider(null);
      }
      void persistPreferences({ collab: next });
      return next;
    });
  }

  return {
    collabEnabled,
    yDoc,
    provider,
    setCollabEnabled,
    setYDoc,
    setProvider,
    handleToggleCollab,
  };
}
