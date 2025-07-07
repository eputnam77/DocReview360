import React from "react";

export interface SelectProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string;
  onValueChange?: (value: string) => void;
}

export function Select({ children, ...props }: SelectProps) {
  return <div {...props}>{children}</div>;
}

export function SelectTrigger(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}

export function SelectValue(props: React.HTMLAttributes<HTMLSpanElement>) {
  return <span {...props} />;
}

export function SelectContent(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}

export function SelectItem(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}
