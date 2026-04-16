import { redirect } from "next/navigation"
import { auth } from "@/auth"
import type { MetricsSummary, SentimentReport } from "@/lib/types"
import AdminDashboardContent from "./AdminDashboardContent"

export const metadata = {
  title: "Admin Dashboard — NexaFlow",
}

export default async function AdminDashboardPage() {
  const session = await auth()

  if (!session || session.user.role !== "admin") {
    redirect("/login")
  }

  const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000"

  let metrics: MetricsSummary | null = null
  let sentimentReport: SentimentReport | null = null

  const [metricsRes, sentimentRes] = await Promise.allSettled([
    fetch(`${fastapiUrl}/metrics/summary`, { cache: "no-store" }),
    fetch(`${fastapiUrl}/metrics/sentiment-report`, { cache: "no-store" }),
  ])

  if (metricsRes.status === "fulfilled" && metricsRes.value.ok) {
    metrics = await metricsRes.value.json()
  } else {
    console.error("Failed to fetch metrics from FastAPI")
  }

  if (sentimentRes.status === "fulfilled" && sentimentRes.value.ok) {
    sentimentReport = await sentimentRes.value.json()
  } else {
    console.error("Failed to fetch sentiment report from FastAPI")
  }

  return (
    <main className="min-h-screen bg-[#0F172A] text-white py-10 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Admin Dashboard</h1>
            <p className="text-slate-400 mt-1 text-sm">
              Welcome back, {session.user.name}
              <span className="ml-2 bg-blue-600 text-xs px-2 py-0.5 rounded">{session.user.role}</span>
            </p>
          </div>
        </div>
        <AdminDashboardContent
          metrics={metrics}
          sentimentReport={sentimentReport}
          user={{ name: session.user.name ?? "", role: session.user.role }}
        />
      </div>
    </main>
  )
}
