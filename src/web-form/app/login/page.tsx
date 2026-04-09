import { redirect } from "next/navigation"
import { auth } from "@/auth"
import LoginForm from "./LoginForm"

export const metadata = {
  title: "NexaFlow Login",
  description: "Sign in to your NexaFlow account",
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
    <main className="min-h-screen bg-[#0F172A] text-white flex items-center justify-center px-4">
      <LoginForm />
    </main>
  )
}
