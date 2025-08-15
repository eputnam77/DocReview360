import { useEffect, useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Approval } from "@/lib/useApprovals";

interface PhaseAdvanceModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  approvals: Approval[];
  checks: string[];
}

export default function PhaseAdvanceModal({
  open,
  onClose,
  onConfirm,
  approvals,
  checks,
}: PhaseAdvanceModalProps) {
  const requiredApprovals = approvals.filter((a) => a.required);
  const [ticked, setTicked] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (open) {
      setTicked({});
    }
  }, [open]);

  const toggle = (id: string, value: boolean) => {
    setTicked((prev) => ({ ...prev, [id]: value }));
  };

  const allApproved = requiredApprovals.every((a) => a.state === "approved");
  const allTicked = checks.every((c) => ticked[c]);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Advance Phase</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {requiredApprovals.length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">Required approvals</p>
              <ul className="space-y-1">
                {requiredApprovals.map((a) => (
                  <li key={a.id} className="flex items-center gap-2 text-sm">
                    {a.state === "approved" ? (
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-600" />
                    )}
                    <span>{a.reviewer}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {checks.length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">Checks</p>
              <ul className="space-y-2">
                {checks.map((c) => (
                  <li key={c} className="flex items-center gap-2">
                    <input
                      id={`check-${c}`}
                      type="checkbox"
                      className="h-4 w-4"
                      checked={ticked[c] || false}
                      onChange={(e) => toggle(c, e.target.checked)}
                    />
                    <label htmlFor={`check-${c}`} className="text-sm">
                      {c}
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {requiredApprovals.length === 0 && checks.length === 0 && (
            <p className="text-sm text-gray-500">
              No checks required for this phase.
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onConfirm} disabled={!allApproved || !allTicked}>
            Advance
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

