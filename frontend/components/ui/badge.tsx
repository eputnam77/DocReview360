// frontend/components/ui/badge.tsx

import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "danger" | "outline";
}

export function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold transition-colors",
        variant === "default" &&
          "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200",
        variant === "success" &&
          "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
        variant === "warning" &&
          "bg-yellow-100 text-yellow-900 dark:bg-yellow-900 dark:text-yellow-200",
        variant === "danger" &&
          "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
        variant === "outline" &&
          "border border-gray-300 dark:border-gray-700 bg-transparent text-gray-800 dark:text-gray-200",
        className,
      )}
      {...props}
    />
  );
}
