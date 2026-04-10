"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Search } from "lucide-react"

export default function TicketSearch() {
  const router = useRouter()
  const [value, setValue] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const id = value.trim().toUpperCase()
    if (!id) { setError("Please enter a ticket ID"); return }
    if (!id.startsWith("TKT-") || id.length < 8) {
      setError("Ticket ID format: TKT-XXXXXXXX")
      return
    }
    setError("")
    router.push(`/ticket/${id}`)
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="flex-1 relative">
        <input
          type="text"
          value={value}
          onChange={e => { setValue(e.target.value); setError("") }}
          placeholder="TKT-XXXXXXXX"
          className="w-full bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg pl-4 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
        />
      </div>
      <button
        type="submit"
        className="flex items-center gap-1.5 bg-[#3B82F6] hover:bg-[#2563EB] text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
      >
        <Search className="w-4 h-4" />
        Track
      </button>
      {error && <p className="absolute mt-10 text-red-400 text-xs">{error}</p>}
    </form>
  )
}
