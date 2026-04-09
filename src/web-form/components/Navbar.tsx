import Link from "next/link"
import { auth, signOut } from "@/auth"
import NexaFlowLogo from "@/components/NexaFlowLogo"

export default async function Navbar() {
  const session = await auth()

  return (
    <nav className="sticky top-0 z-50 bg-[#0F172A]/90 backdrop-blur-sm border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" aria-label="NexaFlow home">
            <NexaFlowLogo />
          </Link>
          <div className="flex items-center gap-6 text-sm text-slate-400">
            <Link href="/" className="hover:text-white transition-colors">
              Home
            </Link>

            {!session && (
              <Link
                href="/login"
                className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-sm font-medium text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
              >
                Login
              </Link>
            )}

            {session?.user?.role === "admin" && (
              <>
                <Link href="/admin/dashboard" className="hover:text-white transition-colors">
                  Admin
                </Link>
                <Link
                  href="/support"
                  className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-sm font-medium text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
                >
                  Get Support
                </Link>
                <form
                  action={async () => {
                    "use server"
                    await signOut({ redirectTo: "/login" })
                  }}
                >
                  <button
                    type="submit"
                    className="text-slate-400 hover:text-white transition-colors"
                  >
                    Logout
                  </button>
                </form>
              </>
            )}

            {session?.user?.role === "agent" && (
              <>
                <Link href="/dashboard" className="hover:text-white transition-colors">
                  Dashboard
                </Link>
                <Link
                  href="/support"
                  className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-sm font-medium text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
                >
                  Get Support
                </Link>
                <form
                  action={async () => {
                    "use server"
                    await signOut({ redirectTo: "/login" })
                  }}
                >
                  <button
                    type="submit"
                    className="text-slate-400 hover:text-white transition-colors"
                  >
                    Logout
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
