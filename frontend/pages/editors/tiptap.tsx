import dynamic from "next/dynamic";
import EditorSkeleton from "../../components/EditorSkeleton";

// Lazy-load the full TipTap editor to defer the CPU cost of loading and
// initialising 25+ ProseMirror extensions until the user navigates here.
const TipTapEditorPage = dynamic(
  () => import("../../components/TiptapEditorFull"),
  { ssr: false, loading: () => <EditorSkeleton /> },
);

export { createTiptapApi } from "../../lib/tiptapApi";
export default TipTapEditorPage;
