"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  Globe,
  Mail,
  MessageSquare,
  Ticket,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import StatusBadge from "@/components/StatusBadge";
import { DashboardSkeleton } from "@/components/LoadingSkeleton";
import type { MetricsSummary, TicketStatus } from "@/lib/types";

interface DashboardContentProps {
  initialMetrics: MetricsSummary | null;
  user: { name: string; role: string };
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function DashboardContent({ initialMetrics, user }: DashboardContentProps) {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(initialMetrics);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshMetrics = async () => {
    try {
      const res = await fetch("/api/metrics");
      if (res.ok) setMetrics(await res.json());
    } catch {
      // keep last known data
    }
  };

  useEffect(() => {
    intervalRef.current = setInterval(refreshMetrics, 30000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  if (!metrics) return <DashboardSkeleton />;

  const statCards = [
    { label: "Total Tickets", value: metrics.total, icon: Ticket, color: "text-[#3B82F6]" },
    { label: "Open", value: metrics.open, icon: AlertCircle, color: "text-yellow-400" },
    { label: "Resolved", value: metrics.resolved, icon: CheckCircle2, color: "text-green-400" },
    {
      label: "Escalation Rate",
      value: `${metrics.escalation_rate}%`,
      icon: ArrowUpRight,
      color: "text-red-400",
    },
  ];

  const channels = [
    { label: "Email", icon: Mail, key: "email" },
    { label: "WhatsApp", icon: MessageSquare, key: "whatsapp" },
    { label: "Web Form", icon: Globe, key: "web_form" },
  ];

  return (
    <div className="space-y-8">
      {/* User header */}
      <div className="flex items-center gap-3">
        <span className="text-slate-300 text-sm">Welcome, {user.name}</span>
        <span className="bg-blue-600 text-xs px-2 py-1 rounded">{user.role}</span>
      </div>
      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="bg-slate-800/50 border-slate-700">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <p className="text-slate-400 text-sm">{label}</p>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <p className={`text-3xl font-bold ${color}`}>{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Channel Breakdown */}
      <div>
        <h2 className="text-lg font-semibold text-slate-200 mb-3">Channel Breakdown</h2>
        <div className="flex gap-4 flex-wrap">
          {channels.map(({ label, icon: Icon, key }) => (
            <Card key={key} className="bg-slate-800/50 border-slate-700 flex-1 min-w-[120px]">
              <CardContent className="p-4 flex items-center gap-3">
                <Icon className="h-5 w-5 text-[#3B82F6]" />
                <div>
                  <p className="text-xs text-slate-400">{label}</p>
                  <p className="text-xl font-bold text-white">
                    {metrics.channels[key] ?? 0}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Recent Tickets Table */}
      <div>
        <h2 className="text-lg font-semibold text-slate-200 mb-3">Recent Tickets</h2>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-700 hover:bg-transparent">
                  <TableHead className="text-slate-400">Ticket ID</TableHead>
                  <TableHead className="text-slate-400 hidden md:table-cell">Channel</TableHead>
                  <TableHead className="text-slate-400 hidden md:table-cell">Category</TableHead>
                  <TableHead className="text-slate-400">Priority</TableHead>
                  <TableHead className="text-slate-400">Status</TableHead>
                  <TableHead className="text-slate-400">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {metrics.recent_tickets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-slate-500 py-8">
                      No tickets yet
                    </TableCell>
                  </TableRow>
                ) : (
                  metrics.recent_tickets.map((t) => (
                    <TableRow
                      key={t.ticket_id}
                      className="border-slate-700 hover:bg-slate-700/30 cursor-pointer"
                    >
                      <TableCell>
                        <Link
                          href={`/ticket/${t.ticket_id}`}
                          className="font-mono text-[#3B82F6] hover:text-[#60A5FA] text-sm"
                        >
                          {t.ticket_id}
                        </Link>
                      </TableCell>
                      <TableCell className="hidden md:table-cell text-slate-300 text-sm capitalize">
                        {(t as unknown as { channel?: string }).channel?.replace("_", " ") ?? "—"}
                      </TableCell>
                      <TableCell className="hidden md:table-cell text-slate-300 text-sm capitalize">
                        {t.category ?? "—"}
                      </TableCell>
                      <TableCell className="text-slate-300 text-sm capitalize">
                        {t.priority}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={t.status as TicketStatus} />
                      </TableCell>
                      <TableCell className="text-slate-400 text-sm">
                        {relativeTime(t.created_at)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
