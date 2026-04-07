import type { Metadata } from "next";
import SupportForm from "./SupportForm";

export const metadata: Metadata = {
  title: "Submit a Support Ticket | NexaFlow",
  description:
    "Submit a support ticket and get AI-powered help from NexaFlow's customer success team.",
  openGraph: {
    type: "website",
    title: "Submit a Support Ticket | NexaFlow",
    description:
      "Submit a support ticket and get AI-powered help from NexaFlow's customer success team.",
  },
};

export default function SupportPage() {
  return (
    <main className="min-h-screen bg-background text-foreground py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white">Get Support</h1>
          <p className="text-slate-400 mt-2">
            Fill out the form below and our AI will respond within hours.
          </p>
        </div>
        <SupportForm />
      </div>
    </main>
  );
}
