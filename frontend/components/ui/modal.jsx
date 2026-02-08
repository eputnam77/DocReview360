// frontend/components/ui/modal.tsx
import * as React from "react";
import * as RadixDialog from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";
export function Modal(props) {
    return <RadixDialog.Root {...props}/>;
}
export function ModalTrigger(props) {
    return <RadixDialog.Trigger {...props}/>;
}
export function ModalContent({ className, children, ...props }) {
    return (<RadixDialog.Portal>
      <RadixDialog.Overlay className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity animate-fade-in"/>
      <RadixDialog.Content className={cn("fixed z-50 left-1/2 top-1/2 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white dark:bg-gray-900 p-6 shadow-xl focus:outline-none animate-modal-in", className)} {...props}>
        {children}
      </RadixDialog.Content>
    </RadixDialog.Portal>);
}
export function ModalHeader({ className, ...props }) {
    return <div className={cn("mb-4", className)} {...props}/>;
}
export function ModalTitle({ className, ...props }) {
    return (<RadixDialog.Title className={cn("text-lg font-semibold", className)} {...props}/>);
}
export function ModalDescription({ className, ...props }) {
    return (<RadixDialog.Description className={cn("text-sm text-gray-500 dark:text-gray-400", className)} {...props}/>);
}
export function ModalFooter({ className, ...props }) {
    return (<div className={cn("mt-6 flex justify-end gap-2", className)} {...props}/>);
}
export function ModalClose(props) {
    return <RadixDialog.Close {...props}/>;
}
