// frontend/components/ui/popover.tsx
import * as React from "react";
import { Popover as HeadlessPopover, Transition } from "@headlessui/react";
import { cn } from "@/lib/utils";
export const Popover = HeadlessPopover;
export const PopoverTrigger = HeadlessPopover.Button;
export const PopoverContent = React.forwardRef(({ className, ...props }, ref) => (<Transition enter="transition duration-100 ease-out" enterFrom="transform scale-95 opacity-0" enterTo="transform scale-100 opacity-100" leave="transition duration-75 ease-out" leaveFrom="transform scale-100 opacity-100" leaveTo="transform scale-95 opacity-0">
    <HeadlessPopover.Panel ref={ref} className={cn("z-50 rounded-md border border-gray-200 bg-white p-3 shadow-md outline-none dark:border-gray-700 dark:bg-gray-900", className)} {...props}/>
  </Transition>));
PopoverContent.displayName = "PopoverContent";
