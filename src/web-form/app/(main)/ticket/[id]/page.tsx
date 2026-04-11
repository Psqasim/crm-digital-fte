import { notFound } from "next/navigation";
import type { Metadata } from "next";
import type { TicketData } from "@/lib/types";
import TicketStatus from "./TicketStatus";
import { auth } from "@/auth";

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

  const [sessionResult, fetchResult] = await Promise.allSettled([
    auth(),
    fetch(`${fastapiUrl}/support/ticket/${id}`, { cache: "no-store" }),
  ]);

  const session = sessionResult.status === "fulfilled" ? sessionResult.value : null;
  const userRole = (session?.user?.role as string | undefined) ?? null;

  let ticket: TicketData | null = null;
  if (fetchResult.status === "fulfilled") {
    const res = fetchResult.value;
    if (res.status === 404) notFound();
    if (res.ok) ticket = await res.json();
  }

  return (
    <main className="min-h-screen bg-[#0F172A] text-white py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <TicketStatus initialData={ticket} ticketId={id} userRole={userRole} />
      </div>
    </main>
  );
}
