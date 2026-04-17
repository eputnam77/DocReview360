import type { PropsWithChildren } from "react";

export function FeedbackTab({ children }: PropsWithChildren) {
  return <section id="feedback" className="space-y-6">{children}</section>;
}

export default FeedbackTab;
