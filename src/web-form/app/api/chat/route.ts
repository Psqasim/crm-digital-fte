import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * app/api/chat/route.ts
 * Phase 7B: Next.js proxy to FastAPI /chat/message endpoint.
 *
 * Keeps the FastAPI origin server-side (no CORS from browser to HF Spaces).
 * Frontend calls /api/chat; this route forwards to FASTAPI_URL/chat/message.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const fastapiUrl =
      process.env.FASTAPI_URL ?? "http://localhost:8000";

    const res = await fetch(`${fastapiUrl}/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      {
        reply:
          "I'm having trouble connecting. Please try again or use our support form.",
        session_id: "",
      },
      { status: 503 }
    );
  }
}
