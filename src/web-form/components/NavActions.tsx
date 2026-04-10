"use client"

import { useState, useRef, useEffect } from "react"
import { LogOut, User, UserPlus, KeyRound, ChevronDown } from "lucide-react"
import { signOut } from "next-auth/react"

interface NavActionsProps {
  isAdmin: boolean
  userName: string
  userEmail: string
}

export default function NavActions({ isAdmin, userName, userEmail }: NavActionsProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const handleLogout = async () => {
    await signOut({ callbackUrl: "/login" })
  }

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-slate-400 hover:text-white transition-colors"
        aria-label="Settings"
      >
        <div className="w-7 h-7 rounded-full bg-[#3B82F6]/20 border border-[#3B82F6]/30 flex items-center justify-center">
          <User className="w-3.5 h-3.5 text-[#3B82F6]" />
        </div>
        <ChevronDown className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-52 bg-slate-900 border border-slate-700 rounded-xl shadow-xl py-1 z-50">
          {/* User info */}
          <div className="px-3 py-2 border-b border-slate-800">
            <p className="text-xs font-medium text-white truncate">{userName}</p>
            <p className="text-xs text-slate-500 truncate">{userEmail}</p>
          </div>

          {/* Admin: manage users */}
          {isAdmin && (
            <button
              onClick={() => { setOpen(false); window.location.href = "/admin/dashboard" }}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-800 transition-colors text-left"
            >
              <UserPlus className="w-4 h-4 text-[#3B82F6]" />
              Manage Users
            </button>
          )}

          {/* Change password */}
          <button
            onClick={() => { setOpen(false); window.location.href = "/profile" }}
            className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-slate-800 transition-colors text-left"
          >
            <KeyRound className="w-4 h-4 text-slate-400" />
            Change Password
          </button>

          <div className="border-t border-slate-800 mt-1 pt-1">
            <button
              onClick={handleLogout}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-slate-800 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
