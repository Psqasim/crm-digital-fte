import type { Metadata } from "next";
import type { MetricsSummary } from "@/lib/types";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import DashboardContent from "./DashboardContent";

export const metadata: Metadata = {
  title: "Support Dashboard | NexaFlow",
  description: "Real-time support metrics and ticket management",
  openGraph: {
    title: "Support Dashboard | NexaFlow",
    description: "Real-time support metrics and ticket management",
  },
};

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect("/login");

  let initialMetrics: MetricsSummary | null = null;
  try {
    const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";
    const res = await fetch(`${fastapiUrl}/metrics/summary`, {
      cache: "no-store",
    });
    if (res.ok) initialMetrics = await res.json();
  } catch {
    // Client will fetch on mount
  }

  return (
    <main className="min-h-screen bg-[#0F172A] text-white py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Support Dashboard</h1>
        <p className="text-slate-400 mb-8">
          Welcome, {session.user.name}{" "}
          <span className="bg-blue-600 text-xs px-2 py-1 rounded">{session.user.role}</span>
        </p>
        <DashboardContent initialMetrics={initialMetrics} user={{ name: session.user.name ?? "", role: session.user.role }} />
      </div>
    </main>
  );
}
