// frontend/components/ui/modal.tsx

import * as React from "react";
import * as RadixDialog from "@radix-ui/react-dialog";
import { cn } from "@/lib/utils";

export interface ModalProps extends React.ComponentProps<typeof RadixDialog.Root> {}

export function Modal(props: ModalProps) {
  return <RadixDialog.Root {...props} />;
}

export function ModalTrigger(props: React.ComponentProps<typeof RadixDialog.Trigger>) {
  return <RadixDialog.Trigger {...props} />;
}

export function ModalContent({
  className,
  children,
  ...props
}: React.ComponentProps<typeof RadixDialog.Content>) {
  return (
    <RadixDialog.Portal>
      <RadixDialog.Overlay className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity animate-fade-in" />
      <RadixDialog.Content
        className={cn(
          "fixed z-50 left-1/2 top-1/2 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white dark:bg-gray-900 p-6 shadow-xl focus:outline-none animate-modal-in",
          className
        )}
        {...props}
      >
        {children}
      </RadixDialog.Content>
    </RadixDialog.Portal>
  );
}

export function ModalHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("mb-4", className)} {...props} />
  );
}

export function ModalTitle({
  className,
  ...props
}: React.ComponentProps<typeof RadixDialog.Title>) {
  return (
    <RadixDialog.Title className={cn("text-lg font-semibold", className)} {...props} />
  );
}

export function ModalDescription({
  className,
  ...props
}: React.ComponentProps<typeof RadixDialog.Description>) {
  return (
    <RadixDialog.Description className={cn("text-sm text-gray-500 dark:text-gray-400", className)} {...props} />
  );
}

export function ModalFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("mt-6 flex justify-end gap-2", className)} {...props} />
  );
}

export function ModalClose(props: React.ComponentProps<typeof RadixDialog.Close>) {
  return <RadixDialog.Close {...props} />;
}

