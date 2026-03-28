import React from "react";

export default function EditorSkeleton() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="animate-pulse text-gray-400">Loading editor...</div>
    </div>
  );
}
