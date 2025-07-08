// frontend/pages/editors/codex.tsx
import React, { useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";

// Editor.js loads only on client
const EditorJS = typeof window !== "undefined" ? require("@editorjs/editorjs") : null;

// Optionally: import tools
// import Header from "@editorjs/header";
// import List from "@editorjs/list";

export default function CodexEditorPage() {
  const ejInstance = useRef<any>(null);
  const holder = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!holder.current || ejInstance.current) return;
    // Dynamically import tools to avoid SSR errors
    let isMounted = true;
    import("@editorjs/editorjs").then(({ default: EditorJS }) => {
      if (!isMounted) return;
      ejInstance.current = new EditorJS({
        holder: holder.current!,
        autofocus: true,
        placeholder: "Start writing...",
        tools: {
          // Add more tools if installed
          // header: require("@editorjs/header"),
          // list: require("@editorjs/list"),
        },
        data: {
          blocks: [
            {
              type: "paragraph",
              data: { text: "Welcome to <b>CodeX Editor (Editor.js)</b>!" },
            },
          ],
        },
      });
    });
    return () => {
      isMounted = false;
      if (ejInstance.current && typeof ejInstance.current.destroy === "function") {
        ejInstance.current.destroy();
        ejInstance.current = null;
      }
    };
  }, []);

  const handleSave = async () => {
    if (ejInstance.current) {
      const output = await ejInstance.current.save();
      alert("Output JSON: " + JSON.stringify(output, null, 2));
      // You can POST this to your backend, etc.
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow p-6">
        <h1 className="text-2xl font-bold mb-4">CodeX Editor (Editor.js)</h1>
        {/* Editor container */}
        <div ref={holder} id="codex-editor" className="border rounded min-h-[300px] mb-6 bg-white" />
        <Button onClick={handleSave}>Save</Button>
      </div>
    </div>
  );
}

