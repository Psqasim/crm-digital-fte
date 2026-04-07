import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
      <div className="text-center">
        <p className="text-[#3B82F6] font-mono text-lg mb-2">404</p>
        <h1 className="text-3xl font-bold mb-3">Page not found</h1>
        <p className="text-slate-400 mb-6">
          The page you&apos;re looking for doesn&apos;t exist.
        </p>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-lg px-5 py-2.5 text-sm font-semibold text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
        >
          Return to homepage
        </Link>
      </div>
    </main>
  );
}
