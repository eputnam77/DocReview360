import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { API } from "@/lib/api";
import {
  CheckCircle2,
  Loader2,
  XCircle,
  AlertTriangle,
  FileText,
} from "lucide-react";

interface Approval {
  id: string;
  reviewer: string;
  state: string;
  signed_at?: string;
  signature_provider: string;
  signature_id?: string;
  certificate_url?: string;
}

const statusConfig: Record<
  string,
  { label: string; variant: "default" | "success" | "warning" | "danger"; icon: JSX.Element }
> = {
  approved: {
    label: "Approved",
    variant: "success",
    icon: <CheckCircle2 className="h-4 w-4" />,
  },
  pending: {
    label: "Pending",
    variant: "default",
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
  },
  rejected: {
    label: "Rejected",
    variant: "danger",
    icon: <XCircle className="h-4 w-4" />,
  },
  overdue: {
    label: "Overdue",
    variant: "warning",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
};

const providerLogos: Record<string, string> = {
  documenso: "/providers/documenso.svg",
  local: "/providers/local.svg",
};

export default function ReviewDetailPage() {
  const router = useRouter();
  const { id } = router.query;
  const [approval, setApproval] = useState<Approval | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetch(`${API}/approvals/${id}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setApproval(data))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="p-4">Loading...</p>;
  if (!approval) return <p className="p-4">Approval not found.</p>;

  const status =
    statusConfig[approval.state as keyof typeof statusConfig] ||
    statusConfig.pending;

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-8">
      <div className="max-w-2xl mx-auto bg-white rounded-lg shadow p-6 space-y-4">
        <h1 className="text-2xl font-bold">Review Details</h1>

        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={status.variant} className="flex items-center gap-1">
            {status.icon}
            {status.label}
          </Badge>
          <span className="text-sm text-gray-500">
            {approval.signed_at
              ? `Signed ${new Date(approval.signed_at).toLocaleString()}`
              : "Not signed yet"}
          </span>
        </div>

        <div className="flex items-center gap-2 mt-2">
          {providerLogos[approval.signature_provider] ? (
            <img
              src={providerLogos[approval.signature_provider]}
              alt={approval.signature_provider}
              className="h-6 w-6"
            />
          ) : (
            <FileText className="h-6 w-6 text-gray-400" />
          )}
          <span className="text-sm text-gray-600">
            {approval.signature_provider}
          </span>
        </div>

        {approval.certificate_url && (
          <a
            href={approval.certificate_url}
            className="text-indigo-600 hover:underline block mt-4"
            target="_blank"
            rel="noreferrer"
          >
            View Certificate
          </a>
        )}

        {approval.state === "approved" && approval.signature_id && (
          <a
            href={`/documenso/${approval.signature_id}?approval=${approval.id}`}
            className="text-indigo-600 hover:underline block"
          >
            View Signed Document
          </a>
        )}
      </div>
    </div>
  );
}
