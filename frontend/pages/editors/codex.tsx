import React, { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";

// Only import Editor.js tools on client
let EditorJS: any = null;
let Header: any = null;
let List: any = null;
let Quote: any = null;

if (typeof window !== "undefined") {
  // The CommonJS build exposes the class under .default
  const EJ = require("@editorjs/editorjs");
  EditorJS = EJ.default ?? EJ;
  Header = require("@editorjs/header").default;
  List = require("@editorjs/list").default;
  Quote = require("@editorjs/quote").default;
}

export default function CodexEditorPage() {
  const ejInstance = useRef<any>(null);
  const holder = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!holder.current || ejInstance.current) return;
    let isMounted = true;

    // Dynamically import tools to avoid SSR errors (if you want, but above method is OK)
    ejInstance.current = new EditorJS({
      holder: holder.current!,
      autofocus: true,
      placeholder: "Start writing...",
      tools: {
        header: Header,
        list: List,
        quote: Quote,
      },
      data: {
        blocks: [
          {
            type: "header",
            data: { text: "Welcome to <b>CodeX Editor (Editor.js)</b>!", level: 2 },
          },
          {
            type: "paragraph",
            data: { text: "You can use headings, lists, and blockquotes below." },
          },
        ],
      },
      onReady: () => {
        // You can do more on editor ready if needed
      },
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
    <div className="fixed inset-0 z-30 bg-white flex flex-col">
      <header className="flex items-center gap-2 bg-gray-100 px-6 py-3 border-b">
        <h1 className="text-xl font-bold mr-6">CodeX Editor (Editor.js)</h1>
        <span className="text-gray-500 text-sm">Headings • Lists • Blockquote</span>
        <Button className="ml-auto" onClick={handleSave}>Save</Button>
      </header>
      <main className="flex-1 overflow-auto p-0">
        <div
          ref={holder}
          id="codex-editor"
          className="w-full h-full min-h-[500px] px-8 py-6 bg-white"
          style={{ outline: "none" }}
        />
      </main>
    </div>
  );
}
