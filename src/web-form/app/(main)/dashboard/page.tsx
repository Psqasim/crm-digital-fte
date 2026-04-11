import type { Metadata } from "next";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import MyTicketsContent from "./DashboardContent";

export const metadata: Metadata = {
  title: "My Tickets | NexaFlow",
  description: "Your submitted support tickets",
};

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect("/login");

  return (
    <main className="min-h-screen bg-[#0F172A] text-white py-10 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">My Tickets</h1>
          <p className="text-slate-400 mt-1 text-sm">
            Welcome back, {session.user.name}
            <span className="ml-2 bg-blue-600/20 text-blue-300 text-xs px-2 py-0.5 rounded border border-blue-600/30">
              {session.user.role}
            </span>
          </p>
        </div>
        <MyTicketsContent email={session.user.email ?? ""} role={session.user.role} />
      </div>
    </main>
  );
}
