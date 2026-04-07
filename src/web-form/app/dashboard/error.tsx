"use client";

import Link from "next/link";

interface ErrorProps {
  reset: () => void;
}

export default function DashboardError({ reset }: ErrorProps) {
  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-3">Dashboard unavailable</h1>
        <p className="text-slate-400 mb-6">
          Unable to load metrics. Please try again.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={reset}
            className="inline-flex items-center justify-center rounded-lg px-5 py-2.5 text-sm font-semibold text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
          >
            Try again
          </button>
          <Link href="/" className="text-slate-400 hover:text-slate-200 text-sm mt-2 inline-block">
            Go home
          </Link>
        </div>
      </div>
    </main>
  );
}
