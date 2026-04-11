"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { TicketData, TicketMessage } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";
import { TicketStatusSkeleton } from "@/components/LoadingSkeleton";
import { Badge } from "@/components/ui/badge";
import FadeIn from "@/components/animations/FadeIn";
import { Bot, AlertTriangle, Copy, CheckCheck, UserCircle, Send } from "lucide-react";

interface TicketStatusProps {
  initialData: TicketData | null;
  ticketId: string;
  userRole?: string | null;
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

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handle = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handle}
      className="flex items-center gap-1 text-xs text-slate-400 hover:text-white bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded transition-colors"
    >
      {copied ? (
        <>
          <CheckCheck className="w-3 h-3 text-green-400" />Copied
        </>
      ) : (
        <>
          <Copy className="w-3 h-3" />Copy ID
        </>
      )}
    </button>
  );
}

// ─── Message thread bubble ────────────────────────────────────────────────────

function MessageBubble({ msg }: { msg: TicketMessage }) {
  const isCustomer = msg.role === "customer";
  const isHumanAgent = msg.is_human_agent; // role="agent"
  const isAI = msg.role === "assistant";

  if (isCustomer) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%]">
          <div className="bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-br-sm text-sm break-words">
            {msg.content}
          </div>
          <p className="text-slate-500 text-xs mt-1 text-right">{formatPKT(msg.created_at)}</p>
        </div>
      </div>
    );
  }

  if (isHumanAgent) {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%]">
          <div className="flex items-center gap-1.5 mb-1">
            <UserCircle className="w-3.5 h-3.5 text-teal-400" />
            <span className="text-teal-400 text-xs font-medium">Support Agent</span>
          </div>
          <div className="bg-slate-700 border border-teal-500/30 text-slate-100 px-4 py-2.5 rounded-2xl rounded-bl-sm text-sm break-words">
            {msg.content}
          </div>
          <p className="text-slate-500 text-xs mt-1">{formatPKT(msg.created_at)}</p>
        </div>
      </div>
    );
  }

  if (isAI) {
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%]">
          <div className="flex items-center gap-1.5 mb-1">
            <Bot className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-blue-400 text-xs font-medium">AI Response</span>
          </div>
          <div className="bg-slate-700 border border-blue-500/20 text-slate-100 px-4 py-2.5 rounded-2xl rounded-bl-sm text-sm break-words whitespace-pre-wrap">
            {msg.content}
          </div>
          <p className="text-slate-500 text-xs mt-1">{formatPKT(msg.created_at)}</p>
        </div>
      </div>
    );
  }

  return null;
}

// ─── Agent reply box ──────────────────────────────────────────────────────────

function AgentReplyBox({
  ticketId,
  onReplySent,
}: {
  ticketId: string;
  onReplySent: () => void;
}) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSend = async () => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setSending(true);
    setError(null);
    setSuccess(false);
    try {
      const res = await fetch("/api/agent-reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket_id: ticketId, message: trimmed }),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        setError(json.error ?? "Failed to send reply");
        return;
      }
      setText("");
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      onReplySent();
    } catch {
      setError("Network error — please try again");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="bg-slate-800/60 border border-teal-500/20 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <UserCircle className="w-4 h-4 text-teal-400" />
        <p className="text-teal-400 text-sm font-medium">Reply as Agent</p>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your reply to the customer… (Enter to send, Shift+Enter for new line)"
        rows={3}
        className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2.5 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-teal-500 transition-colors"
      />

      <div className="flex items-center justify-between mt-2">
        <span className="text-slate-500 text-xs">{text.length}/1000 chars</span>
        <div className="flex items-center gap-2">
          {success && (
            <span className="text-green-400 text-xs flex items-center gap-1">
              <CheckCheck className="w-3 h-3" /> Sent
            </span>
          )}
          {error && <span className="text-red-400 text-xs">{error}</span>}
          <button
            onClick={handleSend}
            disabled={!text.trim() || sending || text.length > 1000}
            className="flex items-center gap-1.5 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm px-4 py-1.5 rounded-lg transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
            {sending ? "Sending…" : "Send Reply"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function TicketStatus({
  initialData,
  ticketId,
  userRole,
}: TicketStatusProps) {
  const [ticket, setTicket] = useState<TicketData | null>(initialData);
  const [notFound, setNotFound] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isStaff = userRole === "admin" || userRole === "agent";

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
        if (TERMINAL.has(json.status) && !isStaff) {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      }
    } catch {
      // network error — keep showing last known data
    }
  };

  useEffect(() => {
    if (ticket && TERMINAL.has(ticket.status) && !isStaff) return;
    intervalRef.current = setInterval(fetchTicket, 5000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket?.status]);

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

  if (!ticket) {
    return <TicketStatusSkeleton />;
  }

  const isActive = ticket.status === "open" || ticket.status === "in_progress";
  const isResolved = ticket.status === "resolved";
  const isEscalated = ticket.status === "escalated";

  // Show message thread if we have structured messages; otherwise fall back to legacy view
  const hasMessageThread = ticket.messages && ticket.messages.length > 0;

  return (
    <FadeIn>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <p className="text-slate-400 text-sm">Ticket ID</p>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="font-mono text-lg text-white font-semibold">
                {ticket.ticket_id}
              </p>
              <CopyButton text={ticket.ticket_id} />
            </div>
          </div>
          <StatusBadge status={ticket.status} />
        </div>

        {/* Analyzing indicator */}
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

        {/* Message thread (structured) — shows all customer, AI, agent messages */}
        {hasMessageThread ? (
          <div>
            <p className="text-slate-400 text-sm mb-3">Conversation</p>
            <div className="space-y-3 bg-slate-800/30 border border-slate-700 rounded-lg p-4">
              {ticket.messages!.map((msg, i) => (
                <MessageBubble key={i} msg={msg} />
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Legacy view — customer message + AI response blocks */}
            {ticket.message && (
              <div>
                <p className="text-slate-400 text-sm mb-2">Your message</p>
                <pre className="whitespace-pre-wrap font-sans bg-slate-800 border border-slate-700 p-4 rounded-lg text-slate-200 text-sm">
                  {ticket.message}
                </pre>
              </div>
            )}

            {ticket.ai_response && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Bot className="w-4 h-4 text-[#3B82F6]" />
                  <p className="text-slate-300 text-sm font-medium">AI Response</p>
                </div>
                <div className="bg-[#3B82F6]/5 border border-[#3B82F6]/20 rounded-lg p-4">
                  <pre className="whitespace-pre-wrap font-sans text-slate-200 text-sm leading-relaxed">
                    {ticket.ai_response}
                  </pre>
                </div>
              </div>
            )}
          </>
        )}

        {/* Escalated notice */}
        {isEscalated && (
          <div className="flex gap-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
            <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-yellow-400 font-medium text-sm">Escalated to human agent</p>
              <p className="text-slate-400 text-xs mt-1">
                Your issue needs specialist attention. A human agent will review it during business hours (Mon–Fri 9am–6pm PKT).
              </p>
            </div>
          </div>
        )}

        {/* Agent reply box — only for admin/agent staff */}
        {isStaff && (
          <AgentReplyBox ticketId={ticket.ticket_id} onReplySent={fetchTicket} />
        )}

        {/* Resolved — what next */}
        {isResolved && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
            <p className="text-green-400 font-medium text-sm mb-1">Ticket resolved</p>
            <p className="text-slate-400 text-xs">
              If this didn&apos;t fully solve your issue, submit a new ticket with more details and reference this ID.
            </p>
          </div>
        )}

        {/* Footer links */}
        <div className="pt-2 flex items-center justify-between flex-wrap gap-3">
          <Link
            href="/support"
            className="text-[#3B82F6] hover:text-[#60A5FA] text-sm transition-colors"
          >
            ← Submit another ticket
          </Link>
          <p className="text-slate-600 text-xs font-mono">{ticket.ticket_id}</p>
        </div>
      </div>
    </FadeIn>
  );
}
