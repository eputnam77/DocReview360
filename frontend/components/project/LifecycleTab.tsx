import type { PropsWithChildren } from "react";

export function LifecycleTab({ children }: PropsWithChildren) {
  return <section id="reviewers" className="space-y-6">{children}</section>;
}

export default LifecycleTab;
