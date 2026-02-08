// frontend/components/ui/button.tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";
export const Button = React.forwardRef(({ className, variant = "default", size = "md", asChild = false, type = "button", children, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (<Comp {...(asChild ? {} : { type })} ref={ref} className={cn("inline-flex items-center justify-center rounded-md font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:opacity-60 disabled:pointer-events-none", 
        // Variants
        variant === "default" &&
            "bg-gray-200 text-gray-900 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600", variant === "primary" &&
            "bg-indigo-600 text-white hover:bg-indigo-700 dark:bg-indigo-700 dark:hover:bg-indigo-800", variant === "secondary" &&
            "bg-gray-100 text-gray-900 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700", variant === "outline" &&
            "border border-gray-300 bg-transparent text-gray-800 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800", variant === "danger" &&
            "bg-red-600 text-white hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800", variant === "ghost" &&
            "bg-transparent text-indigo-700 hover:bg-indigo-50 dark:text-indigo-300 dark:hover:bg-indigo-950/30", 
        // Sizes
        size === "sm" && "px-3 py-1 text-xs h-8", size === "md" && "px-4 py-2 text-sm h-10", size === "lg" && "px-5 py-3 text-base h-12", size === "icon" && "h-10 w-10 p-0", className)} {...props}>
        {children}
      </Comp>);
});
Button.displayName = "Button";
