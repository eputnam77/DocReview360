import React, { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import {
  Bold,
  Italic,
  Strikethrough,
  List,
  ListOrdered,
  Undo2,
  Redo2,
  Pencil,
} from "lucide-react";

/**
 * DocEditorCard – aligns visually with other DocuFlow pages
 * ----------------------------------------------------------
 * Click the “Edit Document” button to open a TipTap editor
 * inside a modal dialog. Includes a lightweight toolbar.
 */
export default function DocEditorCard() {
  const [open, setOpen] = useState(false);

  const editor = useEditor({
    extensions: [StarterKit],
    content: "<p>Start editing your document here…</p>",
  });

  const handleSave = () => {
    if (editor) {
      // Replace with real save logic
      console.log(editor.getHTML());
    }
    setOpen(false);
  };

  /** Toolbar button helper */
  const MenuButton = ({
    icon: Icon,
    action,
    isActive,
    disabled,
  }: {
    icon: any;
    action: () => void;
    isActive?: boolean;
    disabled?: boolean;
  }) => (
    <button
      type="button"
      onClick={action}
      disabled={disabled}
      className={`p-1.5 rounded-md hover:bg-gray-200/70 dark:hover:bg-gray-700/40 transition-colors ${
        isActive ? "bg-indigo-100 text-indigo-600 dark:bg-indigo-900/40" : "text-gray-600 dark:text-gray-300"
      } disabled:opacity-40`}
    >
      <Icon className="w-4 h-4" />
    </button>
  );

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <Card className="shadow-lg rounded-2xl">
        <CardHeader className="flex items-center justify-between bg-gray-50 border-b px-6 py-4">
          <CardTitle className="text-2xl font-bold flex items-center gap-2">
            <Pencil className="w-6 h-6 text-indigo-600" /> Document Editor
          </CardTitle>
          <Button onClick={() => setOpen(true)} className="gap-2">
            <Pencil className="w-4 h-4" /> Edit Document
          </Button>
        </CardHeader>
        <CardContent className="py-8 px-6 bg-white dark:bg-gray-950">
          <p className="text-gray-600 dark:text-gray-400">
            Click “Edit Document” to open a rich‑text editor with bold, italic, lists, and more.
          </p>
        </CardContent>
        <CardFooter className="flex justify-between items-center bg-gray-50 border-t px-6 py-4 text-xs text-gray-400 dark:text-gray-500">
          Changes autosave locally (demo only)
          <Button variant="ghost" size="sm">
            View History
          </Button>
        </CardFooter>
      </Card>

      {/* ───────────────────────── Dialog ───────────────────────── */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl w-full p-0 overflow-hidden">
          <DialogHeader className="bg-gray-100 px-6 py-4 border-b">
            <DialogTitle>Editing Document</DialogTitle>
          </DialogHeader>

          {/* Toolbar */}
          {editor && (
            <div className="flex gap-1 px-6 py-3 border-b bg-white dark:bg-gray-950">
              <MenuButton icon={Bold} action={() => editor.chain().focus().toggleBold().run()} isActive={editor.isActive("bold")} />
              <MenuButton icon={Italic} action={() => editor.chain().focus().toggleItalic().run()} isActive={editor.isActive("italic")} />
              <MenuButton icon={Strikethrough} action={() => editor.chain().focus().toggleStrike().run()} isActive={editor.isActive("strike")} />
              <span className="mx-2 w-px bg-gray-200 dark:bg-gray-800" />
              <MenuButton icon={List} action={() => editor.chain().focus().toggleBulletList().run()} isActive={editor.isActive("bulletList")} />
              <MenuButton icon={ListOrdered} action={() => editor.chain().focus().toggleOrderedList().run()} isActive={editor.isActive("orderedList")} />
              <span className="mx-2 w-px bg-gray-200 dark:bg-gray-800" />
              <MenuButton icon={Undo2} action={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} />
              <MenuButton icon={Redo2} action={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} />
            </div>
          )}

          {/* Editor */}
          <div className="px-6 py-4 bg-white dark:bg-gray-950">
            {editor && (
              <EditorContent
                editor={editor}
                className="min-h-[350px] border border-gray-200 dark:border-gray-800 rounded-lg p-4 focus:outline-none bg-gray-50 dark:bg-gray-900 prose dark:prose-invert"
              />
            )}
          </div>

          <DialogFooter className="flex justify-end gap-2 bg-gray-50 dark:bg-gray-900 px-6 py-4 border-t">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
