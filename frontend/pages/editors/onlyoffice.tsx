import dynamic from "next/dynamic";

import { SectionErrorBoundary } from "../../components";
import EditorSkeleton from "../../components/EditorSkeleton";

const OnlyofficePage = dynamic(
  () => import("../../components/OnlyofficeBackup"),
  { ssr: false, loading: () => <EditorSkeleton /> },
);

export default function OnlyofficePageWithBoundary() {
  return (
    <SectionErrorBoundary label="Editor">
      <OnlyofficePage />
    </SectionErrorBoundary>
  );
}
