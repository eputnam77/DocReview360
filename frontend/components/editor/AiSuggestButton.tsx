import React, { useState } from "react";
import dynamic from "next/dynamic";
import { authenticatedFetch } from "@/lib/api";

const Loader2 = dynamic(() => import("lucide-react").then((m) => m.Loader2));

export interface NewSuggestion {
  from: number;
  to: number;
  original: string;
  suggestion: string;
}

interface AiSuggestButtonProps {
  editor: any;
  aiSuggestEnabled: boolean;
  onNewSuggestion?: (data: NewSuggestion) => void;
}

export default function AiSuggestButton({
  editor,
  aiSuggestEnabled,
  onNewSuggestion,
}: AiSuggestButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSuggest() {
    setError(null);
    if (!editor) return;
    setLoading(true);

    const { from, to, empty } = editor.state.selection;
    const selectedText = empty
      ? editor.state.doc.textContent
      : editor.state.doc.textBetween(from, to, " ");

    try {
      const res = await authenticatedFetch("/ai/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: selectedText,
        }),
      });
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || "AI rewrite failed");
      }
      const data = await res.json();
      const suggestion = data?.result ?? data?.suggestion;
      if (!suggestion) {
        throw new Error("AI rewrite returned no content");
      }

      if (aiSuggestEnabled && onNewSuggestion) {
        onNewSuggestion({ from, to, original: selectedText, suggestion });
      } else {
        editor.chain().focus();
        if (empty) {
          editor.commands.setContent(suggestion);
        } else {
          editor.commands.insertContentAt({ from, to }, suggestion);
        }
      }
    } catch (err: any) {
      setError(err.message || "AI Suggest failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <span className="ml-2 relative">
      <button
        onClick={handleSuggest}
        disabled={loading}
        className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-1"
        title="AI Suggest (rewrite selection)"
      >
        {loading ? (
          <Loader2 className="animate-spin w-4 h-4" />
        ) : (
          <span>AI Suggest</span>
        )}
      </button>
      {error && (
        <div className="absolute left-0 mt-2 bg-red-50 text-red-800 px-2 py-1 text-xs rounded shadow z-50">
          {error}
        </div>
      )}
    </span>
  );
}
