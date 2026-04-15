// Version history drawer for the project detail page.
// Extracted from pages/projects/[id]/index.tsx (R-09).

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { VersionEntry } from "./_types";

export function VersionDrawer({
  open,
  onClose,
  versions,
}: {
  open: boolean;
  onClose: () => void;
  versions: VersionEntry[];
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Document Versions</DialogTitle>
          <DialogDescription className="sr-only">
            Review saved document versions and the author for each change.
          </DialogDescription>
        </DialogHeader>
        <ul className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
          {versions.map((v) => (
            <li key={v.id} className="relative pl-6">
              <span className="absolute left-0 top-1.5 w-3 h-3 bg-indigo-600 rounded-full" />
              <p className="text-sm font-medium">{v.action}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {v.timestamp} — {v.author}
              </p>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
