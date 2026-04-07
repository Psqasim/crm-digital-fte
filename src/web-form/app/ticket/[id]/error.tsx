"use client";

import Link from "next/link";

interface ErrorProps {
  reset: () => void;
}

export default function TicketError({ reset }: ErrorProps) {
  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-3">Error loading ticket</h1>
        <p className="text-slate-400 mb-6">
          We couldn&apos;t load your ticket. Please try again or submit a new one.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={reset}
            className="inline-flex items-center justify-center rounded-lg px-5 py-2.5 text-sm font-semibold text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
          >
            Try again
          </button>
          <Link
            href="/support"
            className="inline-flex items-center justify-center rounded-lg px-5 py-2.5 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 transition-colors"
          >
            Submit new ticket
          </Link>
        </div>
      </div>
    </main>
  );
}
