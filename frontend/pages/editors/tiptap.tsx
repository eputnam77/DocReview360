import dynamic from "next/dynamic";
import EditorSkeleton from "../../components/EditorSkeleton";
import { SectionErrorBoundary } from "../../components";

// Lazy-load the full TipTap editor to defer the CPU cost of loading and
// initialising 25+ ProseMirror extensions until the user navigates here.
const TipTapEditorPage = dynamic(
  () => import("../../components/TiptapEditorFull"),
  { ssr: false, loading: () => <EditorSkeleton /> },
);

function TipTapEditorPageWithBoundary() {
  return (
    <SectionErrorBoundary label="Editor">
      <TipTapEditorPage />
    </SectionErrorBoundary>
  );
}

export { createTiptapApi } from "../../lib/tiptapApi";
export default TipTapEditorPageWithBoundary;
