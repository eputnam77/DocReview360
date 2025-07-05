import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Pencil } from "lucide-react";

export default function DocEditorCard() {
  const [open, setOpen] = useState(false);
  const editor = useEditor({
    extensions: [StarterKit],
    content: "<p>Start editing your document here...</p>",
  });

  const handleSave = () => {
    if (editor) {
      // Replace with your own save logic!
      alert(editor.getHTML());
    }
    setOpen(false);
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <Card className="shadow-xl rounded-2xl">
        <CardHeader className="flex items-center justify-between bg-gray-50 border-b px-6 py-4">
          <CardTitle className="text-2xl font-bold flex items-center gap-2">
            <Pencil className="w-6 h-6 text-blue-500" />
            Document Editor
          </CardTitle>
          <Button variant="outline" onClick={() => setOpen(true)}>
            Open Editor
          </Button>
        </CardHeader>
        <CardContent className="py-8 px-6 bg-white">
          <div className="text-gray-700 mb-4">
            Click “Open Editor” to edit your document with rich formatting, lists, and more.
          </div>
        </CardContent>
        <CardFooter className="flex justify-between items-center bg-gray-50 border-t px-6 py-4">
          <span className="text-xs text-gray-400">All changes autosave (demo only)</span>
          <Button variant="ghost">View History</Button>
        </CardFooter>
      </Card>

      {/* Editor Dialog Modal */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl w-full p-0 overflow-hidden">
          <DialogHeader className="bg-gray-100 px-6 py-4 border-b">
            <DialogTitle>Edit Document</DialogTitle>
          </DialogHeader>
          <div className="px-6 py-4 bg-white">
            {editor && (
              <EditorContent
                editor={editor}
                className="min-h-[350px] border border-gray-200 rounded-xl p-4 focus:outline-none bg-gray-50"
              />
            )}
          </div>
          <DialogFooter className="flex justify-end gap-2 bg-gray-50 px-6 py-4 border-t">
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
