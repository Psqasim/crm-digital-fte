"use client";

/**
 * app/(main)/dashboard/DashboardContent.tsx
 * "My Tickets" — shows only the tickets submitted by the logged-in user's email.
 * Fetches from GET /api/tickets?email=... which proxies FastAPI /support/tickets.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Ticket, RefreshCw, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from "@/components/ui/table";
import StatusBadge from "@/components/StatusBadge";
import type { TicketStatus } from "@/lib/types";

interface MyTicket {
  ticket_id: string;
  subject: string | null;
  category: string | null;
  priority: string;
  status: TicketStatus;
  channel: string | null;
  created_at: string;
}

function formatChannel(channel: string | null | undefined): string {
  switch (channel) {
    case "web_form": return "Web Form";
    case "email":    return "Email";
    case "whatsapp": return "WhatsApp";
    default:         return "Web Form";
  }
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

export default function MyTicketsContent({ email, role }: { email: string; role: string }) {
  const [tickets, setTickets] = useState<MyTicket[] | null>(null);
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    if (!email) return;
    setError(false);
    try {
      const res = await fetch(`/api/tickets?email=${encodeURIComponent(email)}`);
      if (res.ok) setTickets(await res.json());
      else setError(true);
    } catch {
      setError(true);
    }
  };

  useEffect(() => { load(); }, [email]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return (
    <div className="space-y-4">
      {/* Admin shortcut banner */}
      {role === "admin" && (
        <Link
          href="/admin/dashboard"
          className="flex items-center justify-between px-4 py-3 bg-blue-600/10 border border-blue-600/30 rounded-xl text-sm text-blue-300 hover:bg-blue-600/20 hover:text-blue-200 transition-colors"
        >
          <span>You&apos;re an admin — view all system tickets in Admin Dashboard</span>
          <ArrowRight className="w-4 h-4 flex-shrink-0 ml-2" />
        </Link>
      )}

      <div className="flex items-center justify-between">
        <p className="text-slate-400 text-sm">
          Showing tickets submitted from <span className="text-slate-300">{email}</span>
        </p>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <Card className="bg-slate-800/50 border-slate-700">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-700 hover:bg-transparent">
                <TableHead className="text-slate-400">Ticket ID</TableHead>
                <TableHead className="text-slate-400 hidden md:table-cell">Subject</TableHead>
                <TableHead className="text-slate-400 hidden sm:table-cell">Channel</TableHead>
                <TableHead className="text-slate-400">Priority</TableHead>
                <TableHead className="text-slate-400">Status</TableHead>
                <TableHead className="text-slate-400">Submitted</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tickets === null && !error && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-slate-500 py-12">
                    Loading…
                  </TableCell>
                </TableRow>
              )}
              {error && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-red-400 py-12 text-sm">
                    Could not load tickets. Check your connection and refresh.
                  </TableCell>
                </TableRow>
              )}
              {tickets !== null && tickets.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-slate-500 py-12">
                    <Ticket className="w-8 h-8 mx-auto mb-3 opacity-30" />
                    <p className="font-medium">No tickets yet</p>
                    <p className="text-xs mt-1">
                      <Link href="/support" className="text-blue-400 hover:text-blue-300">
                        Submit a support request
                      </Link>{" "}
                      to get started.
                    </p>
                  </TableCell>
                </TableRow>
              )}
              {tickets?.map((t) => (
                <TableRow key={t.ticket_id} className="border-slate-700 hover:bg-slate-700/30">
                  <TableCell>
                    <Link
                      href={`/ticket/${t.ticket_id}`}
                      className="font-mono text-[#3B82F6] hover:text-[#60A5FA] text-sm"
                    >
                      {t.ticket_id}
                    </Link>
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-slate-300 text-sm max-w-[200px] truncate">
                    {t.subject ?? "—"}
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-slate-300 text-sm">
                    {formatChannel(t.channel)}
                  </TableCell>
                  <TableCell className="text-slate-300 text-sm capitalize">
                    {t.priority}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={t.status} />
                  </TableCell>
                  <TableCell className="text-slate-400 text-sm">
                    {relativeTime(t.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
