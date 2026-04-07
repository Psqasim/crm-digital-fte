import Link from "next/link";
import NexaFlowLogo from "@/components/NexaFlowLogo";
import ThemeToggle from "@/components/ThemeToggle";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 bg-background/90 backdrop-blur-sm border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" aria-label="NexaFlow home">
            <NexaFlowLogo />
          </Link>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link
              href="/support"
              className="inline-flex items-center justify-center rounded-lg px-3 py-1.5 text-sm font-medium text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors"
            >
              Get Support
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
