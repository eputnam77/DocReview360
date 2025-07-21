// frontend/components/ui/file-input.tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export type FileInputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const FileInput = React.forwardRef<HTMLInputElement, FileInputProps>(
  ({ className, ...props }, ref) => (
    <input
      type="file"
      ref={ref}
      className={cn(
        "w-full rounded border border-gray-300 p-2 text-sm file:mr-4 file:rounded file:border-0 file:bg-indigo-600 file:px-3 file:py-2 file:text-white hover:file:bg-indigo-700",
        className,
      )}
      {...props}
    />
  ),
);

FileInput.displayName = "FileInput";
