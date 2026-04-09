"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
})

type LoginFormData = z.infer<typeof loginSchema>

export default function LoginForm() {
  const router = useRouter()
  const [authError, setAuthError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    setAuthError(null)

    const result = await signIn("credentials", {
      email: data.email,
      password: data.password,
      redirect: false,
    })

    setIsLoading(false)

    if (result?.error) {
      setAuthError("Invalid email or password")
      return
    }

    // Fetch session to determine role-based redirect
    const sessionRes = await fetch("/api/auth/session")
    const session = await sessionRes.json()

    if (session?.user?.role === "admin") {
      router.push("/admin/dashboard")
    } else {
      router.push("/dashboard")
    }
  }

  return (
    <div className="w-full max-w-sm">
      <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-8 mx-auto mt-20">
        <h1 className="text-2xl font-bold text-white mb-2">Sign in</h1>
        <p className="text-slate-400 text-sm mb-6">NexaFlow Support Portal</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="email" className="text-slate-300 text-sm mb-1 block">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="you@nexaflow.com"
              className="bg-slate-900 border-slate-600 text-white placeholder-slate-500"
              {...register("email")}
              disabled={isLoading}
            />
            {errors.email && (
              <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="password" className="text-slate-300 text-sm mb-1 block">
              Password
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              className="bg-slate-900 border-slate-600 text-white placeholder-slate-500"
              {...register("password")}
              disabled={isLoading}
            />
            {errors.password && (
              <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>
            )}
          </div>

          {authError && (
            <p className="text-red-400 text-sm text-center">{authError}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg transition-colors"
          >
            {isLoading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  )
}
