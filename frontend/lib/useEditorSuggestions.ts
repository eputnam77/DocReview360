import { useState } from "react";

export interface NewSuggestion {
  from: number;
  to: number;
  original: string;
  suggestion: string;
}

export interface Suggestion extends NewSuggestion {
  id: number;
}

export interface EditorSuggestionsState {
  suggestions: Suggestion[];
  handleNewSuggestion: (data: NewSuggestion) => void;
  acceptSuggestion: (id: number) => void;
  rejectSuggestion: (id: number) => void;
  clearSuggestions: () => void;
}

export function useEditorSuggestions(editor: any): EditorSuggestionsState {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);

  function handleNewSuggestion(data: NewSuggestion) {
    setSuggestions((prev) => [
      ...prev,
      { ...data, id: Date.now() + Math.random() },
    ]);
  }

  function acceptSuggestion(id: number) {
    const s = suggestions.find((x) => x.id === id);
    if (s && editor) {
      editor.chain().focus().insertContentAt({ from: s.from, to: s.to }, s.suggestion).run();
    }
    setSuggestions((prev) => prev.filter((x) => x.id !== id));
  }

  function rejectSuggestion(id: number) {
    setSuggestions((prev) => prev.filter((x) => x.id !== id));
  }

  function clearSuggestions() {
    setSuggestions([]);
  }

  return { suggestions, handleNewSuggestion, acceptSuggestion, rejectSuggestion, clearSuggestions };
}
