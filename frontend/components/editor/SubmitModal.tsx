import React from "react";
import { toast } from "react-hot-toast";

export interface SubmitModalProps {
  show: boolean;
  done: boolean;
  projectId: string | null;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

export default function SubmitModal({
  show,
  done,
  projectId,
  onConfirm,
  onClose,
}: SubmitModalProps) {
  if (!show) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Submit document for review"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40"
    >
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 w-96 space-y-4">
        {done ? (
          <>
            <h2 className="text-base font-semibold text-green-700">Submitted!</h2>
            <p className="text-sm text-gray-600">
              Your document has been saved as a new revision and submitted for review.
              {projectId ? " Return to the project to track reviewer progress." : ""}
            </p>
            <div className="flex justify-end gap-2">
              {projectId && (
                <a
                  href={`/projects/${projectId}`}
                  className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
                >
                  Go to Project
                </a>
              )}
              <button className="px-3 py-1.5 border rounded text-sm" onClick={onClose}>
                Close
              </button>
            </div>
          </>
        ) : (
          <>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Submit for Review
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              This will save a final revision of the document and mark it as submitted. Assigned
              reviewers will be notified.
            </p>
            <div className="flex justify-end gap-2">
              <button className="px-3 py-1.5 border rounded text-sm" onClick={onClose}>
                Cancel
              </button>
              <button
                className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
                onClick={async () => {
                  await onConfirm();
                  toast.success("Document submitted for review.");
                }}
              >
                Confirm Submit
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
