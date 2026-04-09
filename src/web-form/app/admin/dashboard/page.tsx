import { redirect } from "next/navigation"
import { auth } from "@/auth"
import AdminDashboardContent from "./AdminDashboardContent"

export const metadata = {
  title: "Admin Dashboard — NexaFlow",
  description: "NexaFlow admin dashboard",
}

export default async function AdminDashboardPage() {
  const session = await auth()

  if (!session || session.user.role !== "admin") {
    redirect("/login")
  }

  const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000"
  let tickets: unknown[] = []
  try {
    const res = await fetch(`${fastapiUrl}/api/tickets`, { cache: "no-store" })
    if (res.ok) tickets = await res.json()
  } catch {
    console.error("Failed to fetch tickets from FastAPI")
  }

  return (
    <main className="min-h-screen bg-[#0F172A] text-white py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Admin Dashboard</h1>
        <p className="text-slate-400 mb-8">
          Welcome, {session.user.name} &mdash;{" "}
          <span className="bg-blue-600 text-xs px-2 py-1 rounded">{session.user.role}</span>
        </p>
        <AdminDashboardContent tickets={tickets} user={{ name: session.user.name ?? "", role: session.user.role }} />
      </div>
    </main>
  )
}
