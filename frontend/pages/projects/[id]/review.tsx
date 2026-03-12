/**
 * @deprecated Superseded by the Feedback tab in the main project view.
 * This page now redirects to /projects/[id]#feedback (Item 44).
 */
import React, { useEffect } from "react";
import { useRouter } from "next/router";

export default function ProjectReviewPage() {
  const router = useRouter();
  const id = router.isReady ? (router.query.id as string | undefined) : undefined;

  useEffect(() => {
    if (id) {
      void router.replace(`/projects/${id}#feedback`);
    }
  }, [id, router]);

  return (
    <div className="p-4 space-y-4 animate-pulse">
      <div className="h-6 w-1/3 bg-gray-200 rounded" />
      <div className="h-4 w-full bg-gray-200 rounded" />
      <div className="h-4 w-5/6 bg-gray-200 rounded" />
    </div>
  );
}
