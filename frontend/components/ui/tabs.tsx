import React from "react";

export interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue?: string;
}

export function Tabs({ children, ...props }: TabsProps) {
  return <div {...props}>{children}</div>;
}

export function TabsList(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}

export function TabsTrigger(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} />;
}

export function TabsContent(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props} />;
}
