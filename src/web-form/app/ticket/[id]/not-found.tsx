import Link from "next/link";

export default function TicketNotFound() {
  return (
    <main className="min-h-screen bg-[#0F172A] text-white flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-3">Ticket not found</h1>
        <p className="text-slate-400 mb-6">
          The ticket you&apos;re looking for doesn&apos;t exist or has been removed.
        </p>
        <Link
          href="/support"
          className="inline-flex items-center justify-center rounded-lg px-5 py-2.5 text-sm font-semibold text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
        >
          Submit a new ticket →
        </Link>
      </div>
    </main>
  );
}
