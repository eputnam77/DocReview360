// frontend/components/ui/select.tsx
import * as React from "react";
import * as RadixSelect from "@radix-ui/react-select";
import { cn } from "@/lib/utils";
import { ChevronDown, Check } from "lucide-react";
// Top-level Select wrapper
export const Select = RadixSelect.Root;
// Button to trigger select
export const SelectTrigger = React.forwardRef(({ className, children, ...props }, ref) => (<RadixSelect.Trigger ref={ref} className={cn("inline-flex items-center justify-between rounded-md border border-gray-300 bg-white px-3 py-2 text-sm ring-offset-white transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:ring-offset-gray-950", className)} {...props}>
    {children}
    <ChevronDown className="ml-2 h-4 w-4 opacity-50"/>
  </RadixSelect.Trigger>));
SelectTrigger.displayName = "SelectTrigger";
// Value displayed in the trigger
export const SelectValue = RadixSelect.Value;
// Dropdown content panel
export const SelectContent = React.forwardRef(({ className, children, ...props }, ref) => (<RadixSelect.Portal>
    <RadixSelect.Content ref={ref} className={cn("z-50 min-w-[8rem] overflow-hidden rounded-md border border-gray-200 bg-white p-1 text-gray-900 shadow-md animate-in fade-in dark:border-gray-800 dark:bg-gray-950 dark:text-gray-100", className)} {...props}>
      <RadixSelect.Viewport>{children}</RadixSelect.Viewport>
    </RadixSelect.Content>
  </RadixSelect.Portal>));
SelectContent.displayName = "SelectContent";
// Each selectable item in dropdown
export const SelectItem = React.forwardRef(({ className, children, ...props }, ref) => (<RadixSelect.Item ref={ref} className={cn("relative flex cursor-pointer select-none items-center rounded-sm py-2 px-3 text-sm outline-none transition-colors hover:bg-indigo-50 focus:bg-indigo-50 dark:hover:bg-gray-800 dark:focus:bg-gray-800", "data-[state=checked]:bg-indigo-100 dark:data-[state=checked]:bg-indigo-900/50 font-medium", className)} {...props}>
    <RadixSelect.ItemIndicator className="absolute left-1 flex h-3 w-3 items-center justify-center">
      <Check className="h-3 w-3 text-indigo-600"/>
    </RadixSelect.ItemIndicator>
    <RadixSelect.ItemText>{children}</RadixSelect.ItemText>
  </RadixSelect.Item>));
SelectItem.displayName = "SelectItem";
