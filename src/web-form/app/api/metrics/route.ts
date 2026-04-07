import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";

    const res = await fetch(`${fastapiUrl}/metrics/summary`, {
      cache: "no-store",
    });

    const data = await res.json();
    return NextResponse.json(data, {
      status: res.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Service unavailable" },
      { status: 503 }
    );
  }
}
