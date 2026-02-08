// frontend/components/ProjectSummaryBar.tsx
"use client";
import { Button } from "@/components/ui/button";
import PhaseTabs from "@/components/PhaseTabs";
import { Download, History } from "lucide-react";
import { cn } from "@/lib/utils";
function ProgBar({ value }) {
    const pct = Math.max(0, Math.min(100, value));
    return (<div className="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2">
      <div className={cn("h-2 rounded-full transition-all", pct === 100
            ? "bg-green-500"
            : pct >= 70
                ? "bg-blue-500"
                : pct > 0
                    ? "bg-yellow-400"
                    : "bg-gray-400")} style={{ width: `${pct}%` }}/>
    </div>);
}
export default function ProjectSummaryBar({ project, phases, phaseCounts, onPhaseChange, onExportRaci, onShowVersions, isOwner, }) {
    return (<div className="sticky top-12 z-20 bg-white/90 dark:bg-gray-900/90 backdrop-blur border-b border-gray-200 dark:border-gray-700 py-2 px-4 flex items-center justify-between gap-4">
      <div className="truncate text-sm text-gray-600 dark:text-gray-300 space-x-2">
        <span className="font-mono">{project.number}</span>
        <span>•</span>
        <span className="truncate">{project.title}</span>
        <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300">
          {project.status}
        </span>
        <span className="hidden md:inline ml-4">Accountable: {project.owner}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-36 shrink-0">
          <ProgBar value={project.progress}/>
        </div>
        <PhaseTabs phases={phases} activePhaseId={project.currentPhaseId} counts={phaseCounts} onChange={onPhaseChange}/>
        {isOwner && (<Button size="sm" onClick={onExportRaci}>
            <Download className="w-4 h-4 mr-1"/> RACI CSV
          </Button>)}
        <Button size="icon" variant="ghost" title="Version timeline" aria-label="Open version timeline" onClick={onShowVersions}>
          <History className="w-5 h-5"/>
        </Button>
      </div>
    </div>);
}
