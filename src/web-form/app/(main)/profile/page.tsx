import { redirect } from "next/navigation"
import { auth } from "@/auth"
import ChangePasswordForm from "./ChangePasswordForm"

export const metadata = { title: "Profile — NexaFlow" }

export default async function ProfilePage() {
  const session = await auth()
  if (!session) redirect("/login")

  return (
    <main className="min-h-screen bg-[#0F172A] text-white py-10 px-4">
      <div className="max-w-md mx-auto">
        <h1 className="text-2xl font-bold mb-1">Profile Settings</h1>
        <p className="text-slate-400 text-sm mb-8">{session.user.email}</p>
        <ChangePasswordForm />
      </div>
    </main>
  )
}
