"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface Ticket {
  ticket_id?: string
  id?: string
  channel?: string
  category?: string
  priority?: string
  status?: string
  created_at?: string
}

interface AdminDashboardContentProps {
  tickets: unknown[]
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

export default function AdminDashboardContent({ tickets, user }: AdminDashboardContentProps) {
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateUserData>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { role: "agent" },
  })

  const onCreateUser = async (data: CreateUserData) => {
    setIsSubmitting(true)
    setFormError(null)

    const res = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    })

    setIsSubmitting(false)

    if (res.status === 201) {
      toast.success("User created successfully")
      reset()
    } else if (res.status === 409) {
      setFormError("Email already exists")
    } else if (res.status === 400) {
      const body = await res.json()
      setFormError(body.error ?? "Validation failed")
    } else if (res.status === 401 || res.status === 403) {
      setFormError("Permission denied")
    } else {
      setFormError("Failed to create user")
    }
  }

  const ticketList = tickets as Ticket[]

  return (
    <div className="space-y-10">
      {/* Tickets Table */}
      <section>
        <h2 className="text-xl font-semibold text-slate-200 mb-4">Support Tickets</h2>
        <Card className="bg-slate-800/50 border-slate-700">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="border-slate-700 hover:bg-transparent">
                  <TableHead className="text-slate-400">Ticket ID</TableHead>
                  <TableHead className="text-slate-400 hidden md:table-cell">Channel</TableHead>
                  <TableHead className="text-slate-400 hidden md:table-cell">Category</TableHead>
                  <TableHead className="text-slate-400">Priority</TableHead>
                  <TableHead className="text-slate-400">Status</TableHead>
                  <TableHead className="text-slate-400">Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ticketList.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-slate-500 py-8">
                      No tickets found
                    </TableCell>
                  </TableRow>
                ) : (
                  ticketList.map((t, i) => (
                    <TableRow key={t.ticket_id ?? t.id ?? i} className="border-slate-700 hover:bg-slate-700/30">
                      <TableCell className="font-mono text-[#3B82F6] text-sm">
                        {t.ticket_id ?? t.id ?? "—"}
                      </TableCell>
                      <TableCell className="hidden md:table-cell text-slate-300 text-sm capitalize">
                        {t.channel?.replace("_", " ") ?? "—"}
                      </TableCell>
                      <TableCell className="hidden md:table-cell text-slate-300 text-sm capitalize">
                        {t.category ?? "—"}
                      </TableCell>
                      <TableCell className="text-slate-300 text-sm capitalize">
                        {t.priority ?? "—"}
                      </TableCell>
                      <TableCell className="text-slate-300 text-sm capitalize">
                        {t.status ?? "—"}
                      </TableCell>
                      <TableCell className="text-slate-400 text-sm">
                        {t.created_at ? relativeTime(t.created_at) : "—"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </section>

      {/* Create User Form */}
      <section>
        <h2 className="text-xl font-semibold text-slate-200 mb-4">Create User</h2>
        <Card className="bg-slate-800/50 border-slate-700 max-w-md">
          <CardHeader>
            <CardTitle className="text-white text-base">Add Internal Staff Account</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onCreateUser)} className="space-y-4">
              <div>
                <Label htmlFor="name" className="text-slate-300 text-sm mb-1 block">
                  Full Name
                </Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Jane Smith"
                  className="bg-slate-900 border-slate-600 text-white placeholder-slate-500"
                  {...register("name")}
                  disabled={isSubmitting}
                />
                {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name.message}</p>}
              </div>

              <div>
                <Label htmlFor="create-email" className="text-slate-300 text-sm mb-1 block">
                  Email
                </Label>
                <Input
                  id="create-email"
                  type="email"
                  placeholder="jane@nexaflow.com"
                  className="bg-slate-900 border-slate-600 text-white placeholder-slate-500"
                  {...register("email")}
                  disabled={isSubmitting}
                />
                {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>}
              </div>

              <div>
                <Label htmlFor="create-password" className="text-slate-300 text-sm mb-1 block">
                  Password
                </Label>
                <Input
                  id="create-password"
                  type="password"
                  placeholder="Min 8 characters"
                  className="bg-slate-900 border-slate-600 text-white placeholder-slate-500"
                  {...register("password")}
                  disabled={isSubmitting}
                />
                {errors.password && (
                  <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>
                )}
              </div>

              <div>
                <Label htmlFor="role" className="text-slate-300 text-sm mb-1 block">
                  Role
                </Label>
                <select
                  id="role"
                  className="w-full bg-slate-900 border border-slate-600 text-white rounded-md px-3 py-2 text-sm"
                  {...register("role")}
                  disabled={isSubmitting}
                >
                  <option value="agent">Agent</option>
                  <option value="admin">Admin</option>
                </select>
                {errors.role && <p className="text-red-400 text-xs mt-1">{errors.role.message}</p>}
              </div>

              {formError && (
                <p className="text-red-400 text-sm">{formError}</p>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg transition-colors"
              >
                {isSubmitting ? "Creating…" : "Create User"}
              </button>
            </form>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
