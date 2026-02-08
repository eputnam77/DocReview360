// frontend/components/workflow/StepStatusBadge.tsx
import React from "react";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Loader2, XCircle, User } from "lucide-react";
import { cn } from "@/lib/utils";
const statusConfig = {
    Completed: {
        color: "bg-green-100 text-green-800",
        icon: <CheckCircle2 className="mr-1 h-4 w-4 text-green-600"/>,
        label: "Approved",
    },
    Pending: {
        color: "bg-gray-100 text-gray-700",
        icon: <Loader2 className="mr-1 h-4 w-4 animate-spin text-gray-500"/>,
        label: "Pending",
    },
    Rejected: {
        color: "bg-red-100 text-red-800",
        icon: <XCircle className="mr-1 h-4 w-4 text-red-600"/>,
        label: "Rejected",
    },
};
const StepStatusBadge = ({ step, showUser, }) => {
    const config = statusConfig[step.status] ||
        statusConfig.Pending;
    return (<Badge variant="outline" className={cn("inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium", config.color)}>
      {config.icon}
      {config.label}
      {/* Optionally show the user who completed it */}
      {showUser && step.completedBy && (<span className="ml-2 flex items-center gap-1">
          {step.completedBy.avatar ? (<img src={step.completedBy.avatar} alt={step.completedBy.name} className="h-4 w-4 rounded-full"/>) : (<User className="h-4 w-4 text-gray-400"/>)}
          <span>{step.completedBy.name}</span>
        </span>)}
    </Badge>);
};
export default StepStatusBadge;
