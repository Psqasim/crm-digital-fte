import { notFound } from "next/navigation";
import type { Metadata } from "next";
import type { TicketData } from "@/lib/types";
import TicketStatus from "./TicketStatus";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";
    const res = await fetch(`${fastapiUrl}/support/ticket/${id}`, {
      cache: "no-store",
    });
    if (res.ok) {
      return {
        title: `Ticket ${id} | NexaFlow Support`,
        description: `Track your support ticket status for ${id}`,
        openGraph: {
          title: `Ticket ${id} | NexaFlow Support`,
          description: "Track your support ticket status",
        },
      };
    }
  } catch {
    // fallback below
  }
  return {
    title: "Ticket | NexaFlow Support",
    description: "Track your support ticket status",
    openGraph: {
      title: "Ticket | NexaFlow Support",
      description: "Track your support ticket status",
    },
  };
}

export default async function TicketPage({ params }: Props) {
  const { id } = await params;
  const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";

  let ticket: TicketData | null = null;
  try {
    const res = await fetch(`${fastapiUrl}/support/ticket/${id}`, {
      cache: "no-store",
    });
    if (res.status === 404) notFound();
    if (res.ok) ticket = await res.json();
  } catch {
    // ticket remains null — TicketStatus handles loading state
  }

  return (
    <main className="min-h-screen bg-[#0F172A] text-white py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <TicketStatus initialData={ticket} ticketId={id} />
      </div>
    </main>
  );
}
