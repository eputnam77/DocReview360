import type { PropsWithChildren } from "react";

export function ApprovalsTab({ children }: PropsWithChildren) {
  return <section id="approvals" className="space-y-6">{children}</section>;
}

export default ApprovalsTab;
