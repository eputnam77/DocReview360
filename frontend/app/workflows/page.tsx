// frontend/app/workflows/page.tsx

"use client";
import React, { useState } from "react";
import Sidebar from "@/components/workflow/Sidebar";
import CategoryFilter from "@/components/workflow/CategoryFilter";
import TemplateCard from "@/components/workflow/TemplateCard";
import { CATEGORIES, TEMPLATES } from "@/data";
import type { Category } from "@/types";

// Optional: Replace with shadcn/ui Breadcrumb if you have it
function Breadcrumb() {
  return (
    <nav className="mb-4 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
      <span>Workflows</span>
      <span className="mx-1">/</span>
      <span className="text-indigo-700 dark:text-indigo-300 font-semibold">
        Templates
      </span>
    </nav>
  );
}

export default function WorkflowGalleryPage() {
  const [active, setActive] = useState<Category>("All");

  const filtered =
    active === "All"
      ? TEMPLATES
      : TEMPLATES.filter((t) => t.category === active);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto px-10 py-8">
        {/* Breadcrumbs + Title */}
        <Breadcrumb />
        <h1 className="mb-8 text-2xl font-semibold tracking-tight">
          Pick a template to start with
        </h1>

        <div className="flex gap-8">
          {/* Category Filter */}
          <aside className="w-44 shrink-0">
            <CategoryFilter active={active} onSelect={setActive} />
          </aside>

          {/* Gallery Grid */}
          <section className="grid flex-1 grid-cols-[repeat(auto-fill,minmax(250px,1fr))] gap-6">
            {filtered.map((template) => (
              <TemplateCard key={template.id} template={template} />
            ))}
          </section>
        </div>
      </main>
    </div>
  );
}
