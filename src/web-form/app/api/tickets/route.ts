import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** POST /api/tickets — submit a support ticket */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";

    const res = await fetch(`${fastapiUrl}/support/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: "Service unavailable" }, { status: 503 });
  }
}

/** GET /api/tickets?email=x — return tickets for that email */
export async function GET(request: NextRequest) {
  try {
    const email = request.nextUrl.searchParams.get("email");
    if (!email) return NextResponse.json({ detail: "email required" }, { status: 400 });

    const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";
    const res = await fetch(
      `${fastapiUrl}/support/tickets?email=${encodeURIComponent(email)}`,
      { cache: "no-store" }
    );

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: "Service unavailable" }, { status: 503 });
  }
}
