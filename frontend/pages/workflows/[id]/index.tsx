import React from "react";
import { useRouter } from "next/router";

export default function WorkflowDetailPage() {
  const router = useRouter();
  const { id } = router.query;

  if (!id) {
    return <p className="p-4">Loading…</p>;
  }

  return (
    <main className="p-8 space-y-4">
      <h1 className="text-2xl font-bold">Workflow {id}</h1>
      <p>This route will display workflow details once implemented.</p>
    </main>
  );
}
