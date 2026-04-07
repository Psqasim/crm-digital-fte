import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";

    const res = await fetch(`${fastapiUrl}/support/ticket/${id}`, {
      cache: "no-store",
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { detail: "Service unavailable" },
      { status: 503 }
    );
  }
}
