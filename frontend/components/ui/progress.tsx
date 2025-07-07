import React from "react";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
}

export function Progress({ value, ...props }: ProgressProps) {
  return <div {...props}>{value}%</div>;
}
