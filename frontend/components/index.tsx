// frontend/components/index.tsx

// UI primitives (shadcn/ui)
export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "./ui/card";
export { Button } from "./ui/button";
export { Input } from "./ui/input";
export { FileInput } from "./ui/file-input";
export { Label } from "./ui/label";
export {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "./ui/select";
export { Badge } from "./ui/badge";
export { Progress } from "./ui/progress";
export { Tabs, TabsList, TabsTrigger, TabsContent } from "./ui/tabs";
export {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "./ui/table";
export {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "./ui/dialog";
export { ScrollArea } from "./ui/scroll-area";

// Icons (barrel export from your icons folder)
export * from "./icons";

// Workflow-specific components (named exports)
export { default as Sidebar } from "./workflow/Sidebar";
export { default as TemplateCard } from "./workflow/TemplateCard";
export { default as CategoryFilter } from "./workflow/CategoryFilter";
export { default as ProgressSidebar } from "./workflow/ProgressSidebar";
export { default as StepStatusBadge } from "./workflow/StepStatusBadge";
export { default as CompletedBanner } from "./workflow/CompletedBanner";
export { default as UploadDropzone } from "./workflow/UploadDropzone";
export { default as SearchBar } from "./SearchBar";
export { default as ChatBot } from "./ChatBot";
export { default as EnvironmentSwitcher } from "./EnvironmentSwitcher";
export { default as PhaseTabs } from "./PhaseTabs";

// Add more as your project grows...
// export { default as SomeOtherComponent } from "./workflow/SomeOtherComponent";
