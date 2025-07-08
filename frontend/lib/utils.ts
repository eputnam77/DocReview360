// frontend/lib/utils.ts

import { ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Concatenate and merge class names intelligently.
 * Usage: <div className={cn("bg-white", isActive && "text-blue-600")} />
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Add additional utility functions here as your app grows...

