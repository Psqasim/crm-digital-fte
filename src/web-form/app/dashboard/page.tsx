import type { Metadata } from "next";
import type { MetricsSummary } from "@/lib/types";
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
        <h1 className="text-3xl font-bold mb-8">Support Dashboard</h1>
        <DashboardContent initialMetrics={initialMetrics} />
      </div>
    </main>
  );
}
