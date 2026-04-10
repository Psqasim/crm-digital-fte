import type { Metadata } from "next";
import type { MetricsSummary } from "@/lib/types";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import DashboardContent from "./DashboardContent";

export const metadata: Metadata = {
  title: "Support Dashboard | NexaFlow",
  description: "All tickets — real-time support metrics",
};

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect("/login");

  let initialMetrics: MetricsSummary | null = null;
  try {
    const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";
    const res = await fetch(`${fastapiUrl}/metrics/summary`, { cache: "no-store" });
    if (res.ok) initialMetrics = await res.json();
  } catch {
    // client will retry on mount
  }

  return (
    <main className="min-h-screen bg-[#0F172A] text-white py-10 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Support Dashboard</h1>
          <p className="text-slate-400 mt-1 text-sm">
            Welcome back, {session.user.name}
            <span className="ml-2 bg-blue-600 text-xs px-2 py-0.5 rounded">{session.user.role}</span>
          </p>
        </div>
        <DashboardContent initialMetrics={initialMetrics} user={{ name: session.user.name ?? "", role: session.user.role }} />
      </div>
    </main>
  );
}
