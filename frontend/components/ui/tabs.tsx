// frontend/components/ui/tabs.tsx

import * as React from "react";
import { cn } from "@/lib/utils";

type TabsContextType = {
  value: string;
  setValue: (val: string) => void;
};
const TabsContext = React.createContext<TabsContextType | undefined>(undefined);

export interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue?: string;
  value?: string;
  onValueChange?: (val: string) => void;
}

export function Tabs({
  defaultValue,
  value: controlledValue,
  onValueChange,
  className,
  children,
  ...props
}: TabsProps) {
  const [value, setValue] = React.useState(defaultValue || "");
  const isControlled = controlledValue !== undefined;
  const currentValue = isControlled ? controlledValue : value;
  const setTab = (val: string) => {
    if (!isControlled) setValue(val);
    onValueChange?.(val);
  };
  return (
    <TabsContext.Provider value={{ value: currentValue, setValue: setTab }}>
      <div className={cn("w-full", className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "inline-flex rounded-lg bg-gray-100 p-1 dark:bg-gray-800",
        className
      )}
      role="tablist"
      {...props}
    />
  );
}

export interface TabsTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}
export function TabsTrigger({
  value,
  className,
  ...props
}: TabsTriggerProps) {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error("TabsTrigger must be used within Tabs");
  const isActive = ctx.value === value;
  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      aria-controls={`tab-panel-${value}`}
      tabIndex={isActive ? 0 : -1}
      onClick={() => ctx.setValue(value)}
      className={cn(
        "min-w-[80px] rounded-md px-4 py-1.5 text-sm font-medium transition-colors",
        isActive
          ? "bg-white dark:bg-gray-900 shadow text-indigo-600"
          : "text-gray-600 hover:text-indigo-700 dark:text-gray-300 dark:hover:text-indigo-400",
        className
      )}
      {...props}
    />
  );
}

export interface TabsContentProps
  extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}
export function TabsContent({
  value,
  className,
  children,
  ...props
}: TabsContentProps) {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error("TabsContent must be used within Tabs");
  if (ctx.value !== value) return null;
  return (
    <div
      id={`tab-panel-${value}`}
      role="tabpanel"
      className={cn("mt-3", className)}
      {...props}
    >
      {children}
    </div>
  );
}
