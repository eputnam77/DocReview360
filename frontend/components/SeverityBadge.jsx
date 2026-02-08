import React from "react";
import { Badge } from "@/components/ui/badge";
const severityConfig = {
    info: { variant: "success", label: "Info" },
    warning: { variant: "warning", label: "Warning" },
    error: { variant: "danger", label: "Error" },
};
export function SeverityBadge({ severity = "info" }) {
    const config = severityConfig[severity] ||
        severityConfig.info;
    return (<Badge variant={config.variant} title={config.label} aria-label={config.label}>
      {config.label}
    </Badge>);
}
export function SeverityLegend() {
    return (<div className="flex items-center gap-2" aria-label="Severity legend">
      <span className="text-sm">Severity:</span>
      <SeverityBadge severity="info"/>
      <SeverityBadge severity="warning"/>
      <SeverityBadge severity="error"/>
    </div>);
}
export default SeverityBadge;
