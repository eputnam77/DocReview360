// components/Editor.tsx
import React, { useState } from "react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

interface EditorProps {
  initialValue?: string;
  onSave?: (val: string) => void;
  rows?: number;
  placeholder?: string;
}

const MAX_LEN = 2000;

const Editor: React.FC<EditorProps> = ({
  initialValue = "",
  onSave,
  rows = 10,
  placeholder = "Type your content…",
}) => {
  const [value, setValue] = useState(initialValue);

  const handleSave = () => {
    if (onSave) onSave(value);
  };

  return (
    <form
      className="space-y-2"
      onSubmit={e => {
        e.preventDefault();
        handleSave();
      }}
    >
      <Label htmlFor="editor" className="font-semibold">
        Document Body
      </Label>
      <textarea
        id="editor"
        value={value}
        onChange={e => setValue(e.target.value)}
        rows={rows}
        maxLength={MAX_LEN}
        className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 p-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition"
        placeholder={placeholder}
        spellCheck
      />
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{value.length} / {MAX_LEN} characters</span>
        <Button type="submit" size="sm" disabled={!value.trim()}>
          Save
        </Button>
      </div>
    </form>
  );
};

export default Editor;
