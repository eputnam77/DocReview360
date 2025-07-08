// frontend/components/index.tsx

// UI primitives (shadcn/ui)
export { Card } from "./ui/card";
export { Button } from "./ui/button";
export { Input } from "./ui/input";
export { Label } from "./ui/label";
export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "./ui/select";

// Icons (barrel export from your icons folder)
export * from "./icons";

// Workflow-specific components
export { default as Sidebar } from "./workflow/Sidebar";
export { default as TemplateCard } from "./workflow/TemplateCard";
export { default as CategoryFilter } from "./workflow/CategoryFilter";
export { default as ProgressSidebar } from "./workflow/ProgressSidebar";
export { default as StepStatusBadge } from "./workflow/StepStatusBadge";
export { default as UploadDropzone } from "./workflow/UploadDropzone";

// Add more as your project grows...
// export { default as SomeOtherComponent } from "./workflow/SomeOtherComponent";

