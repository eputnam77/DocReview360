import React from "react";
import { FileText, Users2 } from "lucide-react";
import type { Category, Template } from "@/types";

export const CATEGORIES: Category[] = ["All", "Compliance", "HR", "General"];

export const TEMPLATES: Template[] = [
  {
    id: "ac",
    title: "Advisory Circular",
    description: "Standard FAA advisory circular template",
    category: "Compliance",
    icon: <FileText className="h-5 w-5" />,
  },
  {
    id: "onboarding",
    title: "Employee Onboarding",
    description: "Collect forms and approvals for new hires",
    category: "HR",
    icon: <Users2 className="h-5 w-5" />,
  },
];
