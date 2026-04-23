import dynamic from "next/dynamic";

import { SectionErrorBoundary } from "../../components";
import EditorSkeleton from "../../components/EditorSkeleton";

const CKEditorPage = dynamic(
  () => import("../../components/CKEditorPrimary"),
  { ssr: false, loading: () => <EditorSkeleton /> },
);

export default function CKEditorPageWithBoundary() {
  return (
    <SectionErrorBoundary label="Editor">
      <CKEditorPage />
    </SectionErrorBoundary>
  );
}
