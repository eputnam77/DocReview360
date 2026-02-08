import { useRouter } from "next/router";
import type { ReactElement } from "react";
import { Badge } from "@/components/ui/badge";
import { useApprovals } from "@/lib/useApprovals";
import {
  CheckCircle2,
  Loader2,
  XCircle,
  AlertTriangle,
  FileText,
} from "lucide-react";

const statusConfig: Record<
  string,
  { label: string; variant: "default" | "success" | "warning" | "danger"; icon: ReactElement }
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
  const { approval, isLoading } = useApprovals({ id: id as string });

  if (isLoading)
    return (
      <div className="p-4 space-y-4 animate-pulse">
        <div className="h-6 w-1/3 bg-gray-200 rounded" />
        <div className="h-4 w-full bg-gray-200 rounded" />
        <div className="h-4 w-5/6 bg-gray-200 rounded" />
      </div>
    );
  if (!approval) return <p className="p-4">Approval not found.</p>;

  const status =
    statusConfig[approval.state as keyof typeof statusConfig] ||
    statusConfig.pending;
  const providerKey = approval.signature_provider ?? "";
  const providerLogo = providerLogos[providerKey];

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
            {approval.signedAt
              ? `Signed ${new Date(approval.signedAt).toLocaleString()}`
              : "Not signed yet"}
          </span>
        </div>

        <div className="flex items-center gap-2 mt-2">
          {providerLogo ? (
            <img
              src={providerLogo}
              alt={providerKey}
              className="h-6 w-6"
            />
          ) : (
            <FileText className="h-6 w-6 text-gray-400" />
          )}
          <span className="text-sm text-gray-600">
            {providerKey || "N/A"}
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
