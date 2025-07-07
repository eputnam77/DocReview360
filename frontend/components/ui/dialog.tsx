import React from "react";

export interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function Dialog({ children, ...props }: DialogProps) {
  return <div {...props}>{children}</div>;
}

export function DialogContent(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}

export function DialogHeader(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}

export function DialogTitle(props: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 {...props} />;
}

export function DialogFooter(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}
