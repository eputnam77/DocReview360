import type { PropsWithChildren } from "react";

export function AuditTab({ children }: PropsWithChildren) {
  return <section id="history" className="space-y-6">{children}</section>;
}

export default AuditTab;
