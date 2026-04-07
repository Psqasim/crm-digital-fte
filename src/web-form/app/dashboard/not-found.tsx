import Link from "next/link";

export default function DashboardNotFound() {
  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-3">Dashboard not found</h1>
        <p className="text-slate-400 mb-6">
          The dashboard page could not be found.
        </p>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-lg px-5 py-2.5 text-sm font-semibold text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
        >
          Go home
        </Link>
      </div>
    </main>
  );
}
