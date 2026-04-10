import { redirect } from "next/navigation"
import { auth } from "@/auth"
import LoginForm from "./LoginForm"
import NexaFlowLogo from "@/components/NexaFlowLogo"
import { Shield, Users, Zap } from "lucide-react"

export const metadata = {
  title: "Sign In — NexaFlow CRM",
}

export default async function LoginPage() {
  const session = await auth()

  if (session?.user) {
    if (session.user.role === "admin") {
      redirect("/admin/dashboard")
    } else {
      redirect("/dashboard")
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Brand Panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-[#0F172A] to-slate-900 border-r border-slate-800 flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(59,130,246,0.15),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(59,130,246,0.08),transparent_60%)]" />

        <div className="relative z-10">
          <NexaFlowLogo />
        </div>

        <div className="relative z-10 space-y-8">
          <div>
            <h2 className="text-3xl font-bold text-white leading-tight">
              Your AI-powered<br />
              customer success hub
            </h2>
            <p className="mt-3 text-slate-400 text-base">
              Manage 800+ weekly support tickets across Email, WhatsApp, and Web — all in one place.
            </p>
          </div>

          <div className="space-y-4">
            {[
              { icon: Zap, label: "75% AI Resolution Rate", desc: "Tickets resolved without human escalation" },
              { icon: Shield, label: "Role-Based Access Control", desc: "Admin and Agent roles with full RBAC" },
              { icon: Users, label: "3,000+ Active Accounts", desc: "Serving SMB to mid-market globally" },
            ].map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-3">
                <div className="mt-0.5 flex-shrink-0 w-8 h-8 rounded-lg bg-[#3B82F6]/10 border border-[#3B82F6]/20 flex items-center justify-center">
                  <Icon className="w-4 h-4 text-[#3B82F6]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">{label}</p>
                  <p className="text-xs text-slate-500">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10">
          <p className="text-xs text-slate-600">
            GIAIC Hackathon 5 &mdash; CRM Digital FTE Factory
          </p>
        </div>
      </div>

      {/* Right Form Panel */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 bg-[#0F172A]">
        <div className="lg:hidden mb-8">
          <NexaFlowLogo />
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white">Sign in to your workspace</h1>
            <p className="mt-2 text-sm text-slate-400">Internal staff access only</p>
          </div>

          <LoginForm />

          <div className="mt-6 flex items-center gap-2 text-xs text-slate-600">
            <Shield className="w-3 h-3" />
            <span>Secured with NextAuth.js v5 — JWT sessions</span>
          </div>
        </div>
      </div>
    </div>
  )
}
