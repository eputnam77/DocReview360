// frontend/components/ui/input.tsx
import * as React from "react";
import { cn } from "@/lib/utils";
export const Input = React.forwardRef(({ className, type = "text", ...props }, ref) => (<input type={type} className={cn("flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-gray-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:ring-offset-gray-950 dark:placeholder:text-gray-500", className)} ref={ref} {...props}/>));
Input.displayName = "Input";
