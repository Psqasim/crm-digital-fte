import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";

export async function POST(request: NextRequest) {
  const session = await auth();

  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const role = session.user.role as string | undefined;
  if (role !== "admin" && role !== "agent") {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  let body: { ticket_id: string; message: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (!body.ticket_id || !body.message?.trim()) {
    return NextResponse.json(
      { error: "ticket_id and message are required" },
      { status: 400 }
    );
  }

  const fastapiUrl = process.env.FASTAPI_URL ?? "http://localhost:8000";

  try {
    const res = await fetch(`${fastapiUrl}/agent/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticket_id: body.ticket_id,
        message: body.message.trim(),
        agent_email: session.user.email ?? "",
      }),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { error: "Failed to reach backend" },
      { status: 502 }
    );
  }
}
