// frontend/components/ui/table.tsx
import * as React from "react";
import { cn } from "@/lib/utils";
export function Table({ className, caption, children, ...props }) {
    return (<div className="w-full overflow-auto rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shadow-sm">
      <table className={cn("min-w-full border-collapse text-sm", className)} {...props}>
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>);
}
export function TableHeader({ className, ...props }) {
    return (<thead className={cn("bg-gray-50 dark:bg-gray-900", className)} {...props}/>);
}
export function TableBody({ className, ...props }) {
    return (<tbody className={cn("divide-y divide-gray-100 dark:divide-gray-800", className)} {...props}/>);
}
export function TableFooter({ className, ...props }) {
    return (<tfoot className={cn("bg-gray-50 dark:bg-gray-900", className)} {...props}/>);
}
export function TableRow({ className, ...props }) {
    return (<tr className={cn("hover:bg-indigo-50 dark:hover:bg-gray-900/60 transition-colors", className)} {...props}/>);
}
export function TableHead({ className, scope = "col", ...props }) {
    return (<th scope={scope} className={cn("px-4 py-3 text-left font-semibold text-gray-700 dark:text-gray-200", className)} {...props}/>);
}
export function TableCell({ className, ...props }) {
    return (<td className={cn("px-4 py-3 align-middle text-gray-900 dark:text-gray-100", className)} {...props}/>);
}
