import { useQuery } from "@tanstack/react-query";
import { authenticatedFetch } from "./api";
const defaultRequester = { id: "system", name: "System", avatar: "" };
const resolveStepStatus = (approvals, phaseIndex, currentIndex) => {
    if (approvals.length > 0) {
        const states = approvals.map((approval) => approval.state);
        if (states.some((state) => state === "rejected")) {
            return "Rejected";
        }
        if (states.every((state) => state === "approved")) {
            return "Completed";
        }
        return "Pending";
    }
    if (phaseIndex < currentIndex) {
        return "Completed";
    }
    return "Pending";
};
const resolveCompletedAt = (approvals, status) => {
    if (status !== "Completed") {
        return undefined;
    }
    const timestamps = approvals
        .map((approval) => approval.signed_at)
        .filter((value) => Boolean(value));
    if (timestamps.length === 0) {
        return undefined;
    }
    return timestamps.sort().at(-1);
};
const resolveCompletedBy = (approvals, status) => {
    if (status !== "Completed") {
        return undefined;
    }
    const approver = approvals.find((approval) => approval.reviewer)?.reviewer;
    if (!approver) {
        return undefined;
    }
    return {
        id: approver,
        name: approver,
        avatar: "",
    };
};
export function useWorkflowInstance(id) {
    return useQuery({
        queryKey: ["workflow-instance", id],
        enabled: !!id,
        queryFn: async () => {
            if (!id) {
                return null;
            }
            const workflowRes = await authenticatedFetch(`/workflows/${id}`);
            if (!workflowRes.ok) {
                throw new Error("Failed to fetch workflow");
            }
            const workflow = (await workflowRes.json());
            const approvalsRes = await authenticatedFetch(`/approvals?workflow=${id}`);
            const approvals = approvalsRes.ok ? (await approvalsRes.json()) : [];
            let requestedBy = defaultRequester;
            let startedAt = new Date().toISOString();
            if (workflow.project) {
                const projectRes = await authenticatedFetch(`/projects/${workflow.project}`);
                if (projectRes.ok) {
                    const project = await projectRes.json();
                    requestedBy = {
                        id: project.user ?? workflow.project,
                        name: project.user ?? workflow.project,
                        avatar: "",
                    };
                    startedAt = project.created ?? project.updated ?? startedAt;
                }
            }
            const phases = Array.isArray(workflow.phases) ? workflow.phases : [];
            const currentIndex = Math.max(phases.indexOf(workflow.phase ?? ""), 0);
            const approvalsByPhase = new Map();
            approvals.forEach((approval) => {
                if (!approval.phase_id) {
                    return;
                }
                const bucket = approvalsByPhase.get(approval.phase_id) ?? [];
                bucket.push(approval);
                approvalsByPhase.set(approval.phase_id, bucket);
            });
            const steps = phases.map((phase, index) => {
                const phaseApprovals = approvalsByPhase.get(phase) ?? [];
                const status = resolveStepStatus(phaseApprovals, index, currentIndex);
                const kind = phaseApprovals.length > 0 ? "Approval" : "Form";
                const required = phaseApprovals.some((approval) => approval.required ?? false);
                return {
                    id: `${workflow.id}-${phase}`,
                    order: index + 1,
                    kind,
                    name: phase,
                    status,
                    phaseId: phase,
                    required: required || undefined,
                    completedAt: resolveCompletedAt(phaseApprovals, status),
                    completedBy: resolveCompletedBy(phaseApprovals, status),
                };
            });
            const status = steps.length > 0 && steps.every((step) => step.status === "Completed")
                ? "Completed"
                : "In-Progress";
            return {
                id: workflow.id,
                workflowName: workflow.template ?? workflow.project ?? workflow.id,
                requestedBy,
                startedAt,
                status,
                steps,
                current: Math.min(currentIndex, Math.max(steps.length - 1, 0)),
            };
        },
    });
}
