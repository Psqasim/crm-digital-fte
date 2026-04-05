import type { TicketStatus } from "@/lib/types";

const statusConfig: Record<
  TicketStatus,
  { label: string; className: string }
> = {
  open: {
    label: "Open",
    className:
      "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  },
  in_progress: {
    label: "In Progress",
    className:
      "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  },
  resolved: {
    label: "Resolved",
    className:
      "bg-green-500/20 text-green-400 border border-green-500/30",
  },
  escalated: {
    label: "Escalated",
    className:
      "bg-red-500/20 text-red-400 border border-red-500/30",
  },
};

const fallback = {
  label: "Unknown",
  className: "bg-slate-500/20 text-slate-400 border border-slate-500/30",
};

interface StatusBadgeProps {
  status: TicketStatus;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status] ?? fallback;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
