import Link from "next/link";
import { auth } from "@/auth";

export default async function Footer() {
  const session = await auth();

  return (
    <footer className="mt-auto py-6 border-t border-slate-800 bg-[#0F172A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-500">
        <span>© 2026 NexaFlow. Built with AI — GIAIC Hackathon 5</span>
        <nav className="flex items-center gap-4">
          <Link href="/" className="hover:text-slate-300 transition-colors">Home</Link>
          <Link href="/support" className="hover:text-slate-300 transition-colors">Get Support</Link>
          {session?.user?.role === "admin" && (
            <Link href="/admin/dashboard" className="hover:text-slate-300 transition-colors">Admin</Link>
          )}
          {session?.user?.role === "agent" && (
            <Link href="/dashboard" className="hover:text-slate-300 transition-colors">Dashboard</Link>
          )}
          <a
            href="https://github.com/Psqasim/crm-digital-fte"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-slate-300 transition-colors"
          >
            GitHub
          </a>
        </nav>
      </div>
    </footer>
  );
}
