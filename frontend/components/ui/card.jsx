// frontend/components/ui/card.tsx
import * as React from "react";
import { cn } from "@/lib/utils";
export const Card = React.forwardRef(({ className, ...props }, ref) => (<div ref={ref} className={cn("rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900", className)} {...props}/>));
Card.displayName = "Card";
export const CardHeader = React.forwardRef(({ className, ...props }, ref) => (<div ref={ref} className={cn("px-6 py-4 border-b border-gray-100 dark:border-gray-800", className)} {...props}/>));
CardHeader.displayName = "CardHeader";
export const CardTitle = React.forwardRef(({ className, ...props }, ref) => (<h3 ref={ref} className={cn("text-lg font-semibold leading-tight tracking-tight", className)} {...props}/>));
CardTitle.displayName = "CardTitle";
export const CardDescription = React.forwardRef(({ className, ...props }, ref) => (<p ref={ref} className={cn("text-gray-500 dark:text-gray-400 text-sm mt-1", className)} {...props}/>));
CardDescription.displayName = "CardDescription";
export const CardContent = React.forwardRef(({ className, ...props }, ref) => (<div ref={ref} className={cn("px-6 py-4", className)} {...props}/>));
CardContent.displayName = "CardContent";
export const CardFooter = React.forwardRef(({ className, ...props }, ref) => (<div ref={ref} className={cn("px-6 py-4 border-t border-gray-100 dark:border-gray-800 text-sm", className)} {...props}/>));
CardFooter.displayName = "CardFooter";
