import React, { useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import FAA_AC_TEMPLATE from "@/data/codexTemplates/faa_ac_template";

// Import the CodeX-specific CSS for spacing, headings, etc.
import "@/styles/codex.css";

// Only import Editor.js tools on client
let EditorJS: any = null;
let Header: any = null;
let List: any = null;
let Quote: any = null;
let Delimiter: any = null;

if (typeof window !== "undefined") {
  const EJ = require("@editorjs/editorjs");
  EditorJS = EJ.default ?? EJ;

  const H = require("@editorjs/header");
  Header = H.default ?? H;

  const L = require("@editorjs/list");
  List = L.default ?? L;

  const Q = require("@editorjs/quote");
  Quote = Q.default ?? Q;

  const D = require("@editorjs/delimiter");
  Delimiter = D.default ?? D;
}

function CodexEditorPage() {
  const ejInstance = useRef<any>(null);
  const holder = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!holder.current || ejInstance.current) return;

    ejInstance.current = new EditorJS({
      holder: holder.current!,
      autofocus: true,
      placeholder: "Start writing...",
      tools: {
        header: Header,
        list: List,
        quote: Quote,
        delimiter: Delimiter,
      },
      data: FAA_AC_TEMPLATE, // FAA Advisory Circular template
      onReady: () => {
        // You can do more on editor ready if needed
      },
    });

    return () => {
      if (
        ejInstance.current &&
        typeof ejInstance.current.destroy === "function"
      ) {
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
        <span className="text-gray-500 text-sm">
          Headings • Lists • Blockquote
        </span>
        <Button className="ml-auto" onClick={handleSave}>
          Save
        </Button>
      </header>
      <main className="flex-1 overflow-auto p-0">
        <div
          ref={holder}
          id="codex-editor"
          className="codex-content w-full h-full min-h-[500px] px-8 py-6 bg-white"
          style={{ outline: "none" }}
        />
      </main>
    </div>
  );
}

// Disable SSR to avoid editor initialization on the server
export default dynamic(() => Promise.resolve(CodexEditorPage), {
  ssr: false,
});
