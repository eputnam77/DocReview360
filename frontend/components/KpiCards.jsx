// frontend/components/KpiCards.tsx
"use client";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Users2, CheckCircle2, Clock, BarChart2 } from "lucide-react";
export default function KpiCards({ stats }) {
    const cards = [
        { icon: Users2, label: "Assigned", val: stats.assigned, col: "text-indigo-600" },
        { icon: CheckCircle2, label: "Approved", val: stats.approved, col: "text-emerald-600" },
        { icon: Clock, label: "Pending", val: stats.pending, col: "text-orange-600" },
        { icon: BarChart2, label: "Overdue", val: stats.overdue, col: "text-red-600" },
    ];
    return (<div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
      {cards.map((s) => (<Card key={s.label} className="shadow-sm">
          <CardContent className="flex items-center gap-4 p-4">
            <s.icon className={cn("w-7 h-7", s.col)}/>
            <div>
              <p className="text-base font-bold leading-none">{s.val}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{s.label}</p>
            </div>
          </CardContent>
        </Card>))}
    </div>);
}
