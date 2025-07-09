// frontend/components/ui/card.tsx

import * as React from "react";
import { cn } from "@/lib/utils";

export type CardProps = React.HTMLAttributes<HTMLDivElement>;
export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900",
        className,
      )}
      {...props}
    />
  );
}

export type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;
export function CardHeader({ className, ...props }: CardHeaderProps) {
  return (
    <div
      className={cn(
        "px-6 py-4 border-b border-gray-100 dark:border-gray-800",
        className,
      )}
      {...props}
    />
  );
}

export type CardTitleProps = React.HTMLAttributes<HTMLHeadingElement>;
export function CardTitle({ className, ...props }: CardTitleProps) {
  return (
    <h3
      className={cn(
        "text-lg font-semibold leading-tight tracking-tight",
        className,
      )}
      {...props}
    />
  );
}

export type CardDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;
export function CardDescription({ className, ...props }: CardDescriptionProps) {
  return (
    <p
      className={cn("text-gray-500 dark:text-gray-400 text-sm mt-1", className)}
      {...props}
    />
  );
}

export type CardContentProps = React.HTMLAttributes<HTMLDivElement>;
export function CardContent({ className, ...props }: CardContentProps) {
  return <div className={cn("px-6 py-4", className)} {...props} />;
}

export type CardFooterProps = React.HTMLAttributes<HTMLDivElement>;
export function CardFooter({ className, ...props }: CardFooterProps) {
  return (
    <div
      className={cn(
        "px-6 py-4 border-t border-gray-100 dark:border-gray-800 text-sm",
        className,
      )}
      {...props}
    />
  );
}
