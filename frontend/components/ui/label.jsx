// frontend/components/ui/label.tsx
import * as React from "react";
import { cn } from "@/lib/utils";
export const Label = React.forwardRef(({ className, ...props }, ref) => (<label ref={ref} className={cn("block text-sm font-medium text-gray-700 dark:text-gray-200 peer-disabled:cursor-not-allowed peer-disabled:opacity-70", className)} {...props}/>));
Label.displayName = "Label";
