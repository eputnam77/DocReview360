// frontend/components/ui/dialog.tsx
import * as React from "react";
import * as RadixDialog from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
export function Dialog(props) {
    return <RadixDialog.Root {...props}/>;
}
export function DialogTrigger(props) {
    return <RadixDialog.Trigger {...props}/>;
}
export function DialogContent({ className, ...props }) {
    return (<RadixDialog.Portal>
      <RadixDialog.Overlay className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity"/>
      <RadixDialog.Content className={cn("fixed z-50 left-1/2 top-1/2 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white dark:bg-gray-900 p-6 shadow-xl focus:outline-none", className)} {...props}/>
    </RadixDialog.Portal>);
}
export function DialogHeader({ className, ...props }) {
    return <div className={cn("mb-4", className)} {...props}/>;
}
export function DialogTitle({ className, ...props }) {
    return (<RadixDialog.Title className={cn("text-lg font-semibold", className)} {...props}/>);
}
export function DialogDescription({ className, ...props }) {
    return (<RadixDialog.Description className={cn("text-sm text-gray-500 dark:text-gray-400", className)} {...props}/>);
}
export function DialogFooter({ className, ...props }) {
    return (<div className={cn("mt-6 flex justify-end gap-2", className)} {...props}/>);
}
export function DialogClose(props) {
    return <RadixDialog.Close {...props}/>;
}
