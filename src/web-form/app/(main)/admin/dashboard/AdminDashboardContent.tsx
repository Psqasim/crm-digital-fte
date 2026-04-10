"use client"

import { useState } from "react"
import Link from "next/link"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  AlertCircle, ArrowUpRight, CheckCircle2, Ticket,
  UserPlus, Copy, CheckCheck,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import StatusBadge from "@/components/StatusBadge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { MetricsSummary, TicketStatus } from "@/lib/types"

interface AdminDashboardContentProps {
  metrics: MetricsSummary | null
  user: { name: string; role: string }
}

const createUserSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Valid email required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  role: z.enum(["admin", "agent"]),
})
type CreateUserData = z.infer<typeof createUserSchema>

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

interface CreatedUser { name: string; email: string; password: string; role: string }

function CredentialsCard({ user, onDone }: { user: CreatedUser; onDone: () => void }) {
  const [copied, setCopied] = useState(false)
  const text = `Email: ${user.email}\nPassword: ${user.password}`

  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30 space-y-3">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="w-5 h-5 text-green-400" />
        <p className="text-green-400 font-medium text-sm">User created — share these credentials</p>
      </div>
      <div className="bg-slate-900 rounded-lg p-3 font-mono text-sm space-y-1">
        <p><span className="text-slate-500">Name:</span> <span className="text-white">{user.name}</span></p>
        <p><span className="text-slate-500">Email:</span> <span className="text-white">{user.email}</span></p>
        <p><span className="text-slate-500">Password:</span> <span className="text-white">{user.password}</span></p>
        <p><span className="text-slate-500">Role:</span> <span className="text-blue-400">{user.role}</span></p>
      </div>
      <div className="flex gap-2">
        <button onClick={copy}
          className="flex items-center gap-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded-lg transition-colors">
          {copied ? <><CheckCheck className="w-3.5 h-3.5 text-green-400" />Copied!</> : <><Copy className="w-3.5 h-3.5" />Copy credentials</>}
        </button>
        <button onClick={onDone}
          className="text-xs text-slate-400 hover:text-white px-3 py-1.5 transition-colors">
          Dismiss
        </button>
      </div>
      <p className="text-xs text-slate-500">⚠️ Save these now — password cannot be retrieved later</p>
    </div>
  )
}

export default function AdminDashboardContent({ metrics, user }: AdminDashboardContentProps) {
  const [formError, setFormError] = useState<string | null>(null)
  const [createdUser, setCreatedUser] = useState<CreatedUser | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { register, handleSubmit, reset, getValues, formState: { errors } } = useForm<CreateUserData>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: "agent" },
  })

  const onCreateUser = async (data: CreateUserData) => {
    setIsSubmitting(true)
    setFormError(null)
    setCreatedUser(null)

    const res = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })

    setIsSubmitting(false)

    if (res.status === 201) {
      // Show credentials before resetting form
      setCreatedUser({ name: data.name, email: data.email, password: data.password, role: data.role })
      toast.success(`${data.role === "admin" ? "Admin" : "Agent"} account created for ${data.name}`)
      reset()
    } else if (res.status === 409) {
      setFormError("A user with this email already exists")
    } else {
      const body = await res.json().catch(() => ({}))
      setFormError(body.error ?? "Failed to create user")
    }
  }

  const statCards = metrics ? [
    { label: "Total Tickets", value: metrics.total, icon: Ticket, color: "text-[#3B82F6]" },
    { label: "Open", value: metrics.open, icon: AlertCircle, color: "text-yellow-400" },
    { label: "Resolved", value: metrics.resolved, icon: CheckCircle2, color: "text-green-400" },
    { label: "Escalation Rate", value: `${metrics.escalation_rate}%`, icon: ArrowUpRight, color: "text-red-400" },
  ] : []

  const tickets = metrics?.recent_tickets ?? []

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
      {/* Left: Tickets (2/3 width on XL) */}
      <div className="xl:col-span-2 space-y-6">
        {/* Stat Cards */}
        {metrics && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {statCards.map(({ label, value, icon: Icon, color }) => (
              <Card key={label} className="bg-slate-800/50 border-slate-700">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <p className="text-slate-400 text-xs">{label}</p>
                    <Icon className={`h-4 w-4 ${color}`} />
                  </div>
                </CardHeader>
                <CardContent>
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Tickets Table */}
        <div>
          <h2 className="text-lg font-semibold text-slate-200 mb-3">All Support Tickets</h2>
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-700 hover:bg-transparent">
                    <TableHead className="text-slate-400">Ticket ID</TableHead>
                    <TableHead className="text-slate-400 hidden md:table-cell">Customer</TableHead>
                    <TableHead className="text-slate-400 hidden lg:table-cell">Subject</TableHead>
                    <TableHead className="text-slate-400">Priority</TableHead>
                    <TableHead className="text-slate-400">Status</TableHead>
                    <TableHead className="text-slate-400">Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tickets.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-slate-500 py-12">
                        <Ticket className="w-8 h-8 mx-auto mb-3 opacity-30" />
                        <p className="font-medium">No tickets yet</p>
                        <p className="text-xs mt-1">Tickets appear here once customers submit support requests</p>
                      </TableCell>
                    </TableRow>
                  ) : (
                    tickets.map((t) => (
                      <TableRow key={t.ticket_id} className="border-slate-700 hover:bg-slate-700/30">
                        <TableCell>
                          <Link href={`/ticket/${t.ticket_id}`}
                            className="font-mono text-[#3B82F6] hover:text-[#60A5FA] text-sm">
                            {t.ticket_id}
                          </Link>
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-slate-300 text-sm">{t.customer_name ?? "—"}</TableCell>
                        <TableCell className="hidden lg:table-cell text-slate-300 text-sm max-w-[160px] truncate">{t.subject ?? "—"}</TableCell>
                        <TableCell className="text-slate-300 text-sm capitalize">{t.priority}</TableCell>
                        <TableCell><StatusBadge status={t.status as TicketStatus} /></TableCell>
                        <TableCell className="text-slate-400 text-sm">{relativeTime(t.created_at)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Right: Create User Panel (1/3 width on XL) */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
          <UserPlus className="w-5 h-5 text-[#3B82F6]" />
          Add Staff Account
        </h2>

        {/* Credentials shown after creation */}
        {createdUser && (
          <CredentialsCard user={createdUser} onDone={() => setCreatedUser(null)} />
        )}

        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="pt-5">
            <form onSubmit={handleSubmit(onCreateUser)} className="space-y-4">
              <div>
                <Label htmlFor="name" className="text-slate-300 text-sm mb-1 block">Full Name</Label>
                <Input id="name" type="text" placeholder="Jane Smith"
                  className="bg-slate-900 border-slate-600 text-white placeholder-slate-500"
                  {...register("name")} disabled={isSubmitting} />
                {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name.message}</p>}
              </div>

              <div>
                <Label htmlFor="u-email" className="text-slate-300 text-sm mb-1 block">Email</Label>
                <Input id="u-email" type="email" placeholder="jane@nexaflow.com"
                  className="bg-slate-900 border-slate-600 text-white placeholder-slate-500"
                  {...register("email")} disabled={isSubmitting} />
                {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>}
              </div>

              <div>
                <Label htmlFor="u-password" className="text-slate-300 text-sm mb-1 block">
                  Password
                  <span className="ml-1 text-slate-500 text-xs">(you set this — share with agent)</span>
                </Label>
                <Input id="u-password" type="text" placeholder="Set their login password"
                  className="bg-slate-900 border-slate-600 text-white placeholder-slate-500 font-mono"
                  {...register("password")} disabled={isSubmitting} />
                {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>}
              </div>

              <div>
                <Label htmlFor="u-role" className="text-slate-300 text-sm mb-1 block">Role</Label>
                <select id="u-role"
                  className="w-full bg-slate-900 border border-slate-600 text-white rounded-md px-3 py-2 text-sm"
                  {...register("role")} disabled={isSubmitting}>
                  <option value="agent">Agent — handles tickets</option>
                  <option value="admin">Admin — full access</option>
                </select>
              </div>

              {formError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                  <p className="text-red-400 text-sm">{formError}</p>
                </div>
              )}

              <button type="submit" disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 text-white font-medium py-2.5 rounded-lg transition-colors text-sm">
                {isSubmitting ? "Creating…" : "Create Account"}
              </button>
            </form>
          </CardContent>
        </Card>

        <p className="text-xs text-slate-600 leading-relaxed">
          After creating an account, share the email and password with your team member.
          They can change their password after logging in via Profile Settings.
        </p>
      </div>
    </div>
  )
}
