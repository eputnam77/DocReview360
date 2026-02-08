// frontend/components/workflow/CategoryFilter.tsx
import React from "react";
import { CATEGORIES } from "@/data";
import { cn } from "@/lib/utils";
export default function CategoryFilter({ active, onSelect, className, }) {
    return (<ul className={cn("flex flex-col gap-1", className)}>
      {CATEGORIES.map((category) => (<li key={category}>
          <button type="button" className={cn("w-full rounded-md px-3 py-2 text-left text-sm font-medium transition-colors", active === category
                ? "bg-indigo-50 text-indigo-600 dark:bg-gray-900 dark:text-indigo-400"
                : "text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800")} aria-current={active === category ? "page" : undefined} onClick={() => onSelect(category)}>
            {category}
          </button>
        </li>))}
    </ul>);
}
