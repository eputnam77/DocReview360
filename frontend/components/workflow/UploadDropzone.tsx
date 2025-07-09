// components/workflow/UploadDropzone.tsx
"use client";

import React, { useCallback, useRef, useState } from "react";
import { UploadCloud, X, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadDropzoneProps {
  value?: File | null;
  onChange?: (file: File | null) => void;
  accept?: string; // e.g., "image/*,.pdf"
  maxSizeMB?: number;
}

const UploadDropzone: React.FC<UploadDropzoneProps> = ({
  value,
  onChange,
  accept = "*",
  maxSizeMB = 10,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Open native file picker
  const openFileDialog = () => {
    inputRef.current?.click();
  };

  // Handle files (from input or drop)
  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (files && files.length) {
        const file = files[0];
        if (file.size > maxSizeMB * 1024 * 1024) {
          alert(`File exceeds ${maxSizeMB} MB limit.`);
          return;
        }
        onChange?.(file);
      }
    },
    [onChange, maxSizeMB],
  );

  // Drag events
  const preventDefaults = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  return (
    <>
      <div
        tabIndex={0}
        role="button"
        className={cn(
          "flex h-36 cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed transition-colors",
          dragActive
            ? "border-purple-600 bg-purple-50"
            : "border-muted bg-muted/40",
        )}
        onClick={openFileDialog}
        onKeyDown={(e) => e.key === "Enter" && openFileDialog()}
        onDragEnter={(e) => {
          preventDefaults(e);
          setDragActive(true);
        }}
        onDragLeave={(e) => {
          preventDefaults(e);
          setDragActive(false);
        }}
        onDragOver={preventDefaults}
        onDrop={(e) => {
          preventDefaults(e);
          setDragActive(false);
          handleFiles(e.dataTransfer.files);
        }}
        aria-label="Upload file"
      >
        <UploadCloud className="mb-2 h-7 w-7 text-purple-500" />
        <span className="text-sm font-medium">
          {value ? "Replace file" : "Click to upload or drag & drop"}
        </span>
        <span className="text-xs text-muted-foreground">
          {`Max ${maxSizeMB}MB • Allowed: ${accept}`}
        </span>
      </div>

      {/* Show selected file */}
      {value && (
        <div className="mt-3 flex items-center justify-between rounded-md border px-3 py-2 text-sm bg-white">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span>{value.name}</span>
            <span className="ml-2 text-muted-foreground">
              ({(value.size / 1024 / 1024).toFixed(2)} MB)
            </span>
          </div>
          <button
            type="button"
            className="text-muted-foreground hover:text-red-600"
            aria-label="Remove file"
            onClick={() => onChange?.(null)}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Hidden native input */}
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
        tabIndex={-1}
      />
    </>
  );
};

export default UploadDropzone;
