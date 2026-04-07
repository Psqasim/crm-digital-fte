"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { TicketData } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import { TicketStatusSkeleton } from "@/components/LoadingSkeleton";
import { Badge } from "@/components/ui/badge";
import FadeIn from "@/components/animations/FadeIn";

interface TicketStatusProps {
  initialData: TicketData | null;
  ticketId: string;
}

const PKT = new Intl.DateTimeFormat("en-US", {
  timeZone: "Asia/Karachi",
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});

function formatPKT(iso: string) {
  return PKT.format(new Date(iso)) + " PKT";
}

const TERMINAL = new Set(["resolved", "escalated"]);

export default function TicketStatus({ initialData, ticketId }: TicketStatusProps) {
  const [ticket, setTicket] = useState<TicketData | null>(initialData);
  const [notFound, setNotFound] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTicket = async () => {
    try {
      const res = await fetch(`/api/tickets/${ticketId}`);
      if (res.status === 404) {
        setNotFound(true);
        if (intervalRef.current) clearInterval(intervalRef.current);
        return;
      }
      if (res.ok) {
        const json: TicketData = await res.json();
        setTicket(json);
        if (TERMINAL.has(json.status)) {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      }
    } catch {
      // network error — keep showing last known data
    }
  };

  useEffect(() => {
    // Don't start polling for terminal statuses
    if (ticket && TERMINAL.has(ticket.status)) return;

    intervalRef.current = setInterval(fetchTicket, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket?.status]);

  // Not found state
  if (notFound) {
    return (
      <div className="text-center py-16">
        <h1 className="text-2xl font-bold text-white mb-3">Ticket not found</h1>
        <p className="text-slate-400 mb-6">
          The ticket you&apos;re looking for doesn&apos;t exist or has been removed.
        </p>
        <Link
          href="/support"
          className="inline-flex items-center justify-center rounded-lg px-5 py-2.5 text-sm font-medium text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
        >
          Submit a new ticket →
        </Link>
      </div>
    );
  }

  // Loading skeleton (only when no initialData)
  if (!ticket) {
    return <TicketStatusSkeleton />;
  }

  const isActive = ticket.status === "open" || ticket.status === "in_progress";

  return (
    <FadeIn>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-slate-400 text-sm">Ticket ID</p>
            <p className="font-mono text-lg text-white font-semibold">
              {ticket.ticket_id}
            </p>
          </div>
          <StatusBadge status={ticket.status} />
        </div>

        {/* Typing indicator */}
        {isActive && (
          <div className="flex items-center gap-2 text-slate-400 text-sm">
            <span>AI is analyzing your ticket...</span>
            <span className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce"
                  style={{ animationDelay: `${i * 0.2}s` }}
                />
              ))}
            </span>
          </div>
        )}

        {/* Metadata */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 space-y-3">
          {ticket.subject && (
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wide">Subject</p>
              <p className="text-white mt-0.5">{ticket.subject}</p>
            </div>
          )}

          <div className="flex gap-3 flex-wrap">
            {ticket.category && (
              <div>
                <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Category</p>
                <Badge className="bg-slate-700 text-slate-200 capitalize">
                  {ticket.category}
                </Badge>
              </div>
            )}
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wide mb-1">Priority</p>
              <Badge className="bg-slate-700 text-slate-200 capitalize">
                {ticket.priority}
              </Badge>
            </div>
          </div>

          <div>
            <p className="text-slate-400 text-xs uppercase tracking-wide">Submitted</p>
            <p className="text-white text-sm mt-0.5">{formatPKT(ticket.created_at)}</p>
          </div>

          {ticket.updated_at && (
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wide">Last Updated</p>
              <p className="text-white text-sm mt-0.5">{formatPKT(ticket.updated_at)}</p>
            </div>
          )}
        </div>

        {/* Message */}
        {ticket.message && (
          <div>
            <p className="text-slate-400 text-sm mb-2">Your message</p>
            <pre className="whitespace-pre-wrap font-sans bg-slate-800 border border-slate-700 p-4 rounded-lg text-slate-200 text-sm">
              {ticket.message}
            </pre>
          </div>
        )}

        {/* Back link */}
        <div className="pt-2">
          <Link
            href="/support"
            className="text-[#3B82F6] hover:text-[#60A5FA] text-sm transition-colors"
          >
            ← Submit another ticket
          </Link>
        </div>
      </div>
    </FadeIn>
  );
}
