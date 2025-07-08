// frontend/components/workflow/TemplateCard.tsx

import React from "react";
import { ArrowUpRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { Template } from "@/types";
import { cn } from "@/lib/utils";

interface TemplateCardProps {
  template: Template;
  onClick?: () => void;
  className?: string;
}

const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  onClick,
  className,
}) => {
  return (
    <Card
      className={cn(
        "group relative h-40 cursor-pointer transition-shadow hover:shadow-md",
        className
      )}
      tabIndex={0}
      role="button"
      aria-label={template.title}
      onClick={onClick}
      onKeyDown={e => {
        if (e.key === "Enter" || e.key === " ") onClick?.();
      }}
    >
      <CardContent className="h-full p-4">
        <div className="flex h-full flex-col justify-between">
          {/* Icon and arrow */}
          <div className="flex items-start justify-between">
            {template.icon}
            <ArrowUpRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </div>

          {/* Title and description */}
          <div>
            <h3 className="text-sm font-semibold leading-tight">
              {template.title}
            </h3>
            <p className="mt-1 text-xs text-muted-foreground line-clamp-3">
              {template.description}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default TemplateCard;

