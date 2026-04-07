import type { Metadata } from "next";
import Link from "next/link";
import { Clock, Globe, Zap } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import NexaFlowLogo from "@/components/NexaFlowLogo";
import FadeIn from "@/components/animations/FadeIn";
import SlideUp from "@/components/animations/SlideUp";

export const metadata: Metadata = {
  title: "NexaFlow | Intelligent Customer Support",
  description: "AI-powered 24/7 customer support for NexaFlow SaaS platform",
  openGraph: {
    type: "website",
    title: "NexaFlow | Intelligent Customer Support",
    description: "AI-powered 24/7 customer support for NexaFlow SaaS platform",
  },
};

const features = [
  {
    icon: Clock,
    title: "24/7 AI Support",
    description:
      "Round-the-clock AI assistance resolves 75% of tickets without human escalation.",
  },
  {
    icon: Globe,
    title: "Multi-Channel",
    description:
      "Unified support across Email, WhatsApp, and Web — all in one platform.",
  },
  {
    icon: Zap,
    title: "Smart Routing",
    description:
      "Intelligent escalation routes complex cases to the right human agent instantly.",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#0F172A] text-white">
      {/* Hero */}
      <section className="min-h-[60vh] flex flex-col items-center justify-center px-4 text-center">
        <FadeIn>
          <div className="flex flex-col items-center gap-6">
            <NexaFlowLogo size="lg" />
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight max-w-3xl">
              Intelligent Customer Success Platform
            </h1>
            <p className="text-lg md:text-xl text-slate-400 max-w-2xl">
              24/7 AI-powered support across Email, WhatsApp, and Web
            </p>
            <Link
              href="/support"
              className="inline-flex items-center justify-center rounded-lg px-6 py-3 text-base font-semibold text-white bg-[#3B82F6] hover:bg-[#2563EB] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3B82F6]"
            >
              Get Support
            </Link>
          </div>
        </FadeIn>
      </section>

      {/* Feature Cards */}
      <section className="py-16 px-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {features.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <SlideUp key={feature.title} delay={0.1 * i}>
                <Card className="bg-slate-800/50 border-slate-700 hover:shadow-[0_0_20px_rgba(59,130,246,0.2)] transition-shadow duration-300 h-full">
                  <CardHeader>
                    <Icon className="h-8 w-8 text-[#3B82F6] mb-2" />
                    <CardTitle className="text-white">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-slate-400">{feature.description}</p>
                  </CardContent>
                </Card>
              </SlideUp>
            );
          })}
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 text-center text-slate-500 text-sm border-t border-slate-800">
        © 2025 NexaFlow. Powered by AI.
      </footer>
    </main>
  );
}
