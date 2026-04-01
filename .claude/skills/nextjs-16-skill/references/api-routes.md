# API Route Handlers

## Basic Route Handler

### GET Request

```typescript
// app/api/tasks/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  const tasks = await db.tasks.findMany();

  return NextResponse.json(tasks);
}
```

### POST Request

```typescript
// app/api/tasks/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const task = await db.tasks.create({
    data: {
      title: body.title,
      description: body.description,
    },
  });

  return NextResponse.json(task, { status: 201 });
}
```

## Dynamic Routes

### Single Parameter

```typescript
// app/api/tasks/[id]/route.ts
import { NextRequest, NextResponse } from "next/server";

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;

  const task = await db.tasks.findUnique({ where: { id } });

  if (!task) {
    return NextResponse.json(
      { error: "Task not found" },
      { status: 404 }
    );
  }

  return NextResponse.json(task);
}

export async function PUT(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;
  const body = await request.json();

  const task = await db.tasks.update({
    where: { id },
    data: body,
  });

  return NextResponse.json(task);
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  const { id } = await params;

  await db.tasks.delete({ where: { id } });

  return new NextResponse(null, { status: 204 });
}
```

### Multiple Parameters

```typescript
// app/api/users/[userId]/tasks/[taskId]/route.ts
interface RouteParams {
  params: Promise<{ userId: string; taskId: string }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { userId, taskId } = await params;

  const task = await db.tasks.findFirst({
    where: { id: taskId, userId },
  });

  return NextResponse.json(task);
}
```

## Request Handling

### Query Parameters

```typescript
// app/api/tasks/route.ts
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;

  const status = searchParams.get("status"); // "completed" | "pending"
  const limit = parseInt(searchParams.get("limit") || "10");
  const page = parseInt(searchParams.get("page") || "1");

  const tasks = await db.tasks.findMany({
    where: status ? { completed: status === "completed" } : undefined,
    take: limit,
    skip: (page - 1) * limit,
  });

  return NextResponse.json({
    tasks,
    pagination: { page, limit },
  });
}
```

### Headers

```typescript
export async function GET(request: NextRequest) {
  // Read headers
  const authHeader = request.headers.get("authorization");
  const contentType = request.headers.get("content-type");

  // Set response headers
  return NextResponse.json(
    { data: "..." },
    {
      headers: {
        "Cache-Control": "public, max-age=3600",
        "X-Custom-Header": "value",
      },
    }
  );
}
```

### Cookies

```typescript
import { cookies } from "next/headers";

export async function GET() {
  const cookieStore = await cookies();

  // Read cookie
  const sessionId = cookieStore.get("sessionId")?.value;

  // Set cookie in response
  return NextResponse.json(
    { data: "..." },
    {
      headers: {
        "Set-Cookie": `sessionId=${newSessionId}; HttpOnly; Path=/`,
      },
    }
  );
}

export async function POST() {
  const cookieStore = await cookies();

  // Set cookie
  cookieStore.set("preference", "dark", {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 7, // 1 week
  });

  return NextResponse.json({ success: true });
}
```

## Response Types

### JSON Response

```typescript
return NextResponse.json({ data: "..." });
return NextResponse.json({ error: "Not found" }, { status: 404 });
```

### Redirect

```typescript
import { redirect } from "next/navigation";

export async function GET() {
  redirect("/new-location");
}

// Or with NextResponse
export async function GET() {
  return NextResponse.redirect(new URL("/new-location", request.url));
}
```

### Stream Response

```typescript
export async function GET() {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      for (let i = 0; i < 10; i++) {
        controller.enqueue(encoder.encode(`data: ${i}\n\n`));
        await new Promise((r) => setTimeout(r, 1000));
      }
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
```

## Error Handling

### Try-Catch Pattern

```typescript
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate
    if (!body.title) {
      return NextResponse.json(
        { error: "Title is required" },
        { status: 400 }
      );
    }

    const task = await db.tasks.create({ data: body });
    return NextResponse.json(task, { status: 201 });

  } catch (error) {
    console.error("API Error:", error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "Validation failed", details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
```

### Zod Validation

```typescript
import { z } from "zod";

const CreateTaskSchema = z.object({
  title: z.string().min(1).max(200),
  description: z.string().max(1000).optional(),
  priority: z.enum(["low", "medium", "high"]).default("medium"),
});

export async function POST(request: NextRequest) {
  const body = await request.json();

  const result = CreateTaskSchema.safeParse(body);

  if (!result.success) {
    return NextResponse.json(
      {
        error: "Validation failed",
        details: result.error.flatten().fieldErrors,
      },
      { status: 400 }
    );
  }

  const task = await db.tasks.create({ data: result.data });
  return NextResponse.json(task, { status: 201 });
}
```

## Authentication

### Check Session

```typescript
import { getSession } from "@/lib/auth";

export async function GET(request: NextRequest) {
  const session = await getSession();

  if (!session) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  const tasks = await db.tasks.findMany({
    where: { userId: session.user.id },
  });

  return NextResponse.json(tasks);
}
```

### API Key Authentication

```typescript
export async function GET(request: NextRequest) {
  const apiKey = request.headers.get("x-api-key");

  if (apiKey !== process.env.API_KEY) {
    return NextResponse.json(
      { error: "Invalid API key" },
      { status: 401 }
    );
  }

  // Continue with authenticated request
}
```

## CORS

```typescript
// app/api/tasks/route.ts
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

export async function OPTIONS() {
  return new Response(null, { headers: corsHeaders });
}

export async function GET() {
  const tasks = await db.tasks.findMany();

  return NextResponse.json(tasks, { headers: corsHeaders });
}
```

## Route Segment Config

```typescript
// app/api/tasks/route.ts

// Force dynamic rendering
export const dynamic = "force-dynamic";

// Set revalidation period
export const revalidate = 60; // seconds

// Set runtime
export const runtime = "edge"; // or "nodejs"

// Set max duration (serverless)
export const maxDuration = 30; // seconds
```

## Proxy to External API

```typescript
// app/api/proxy/[...path]/route.ts
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const backendUrl = `${process.env.BACKEND_URL}/${path.join("/")}`;

  const response = await fetch(backendUrl, {
    headers: {
      Authorization: request.headers.get("authorization") || "",
    },
  });

  const data = await response.json();
  return NextResponse.json(data);
}
```

## Best Practices

### 1. Consistent Error Format

```typescript
interface ApiError {
  error: string;
  message: string;
  details?: unknown;
}

function errorResponse(
  message: string,
  status: number,
  details?: unknown
): NextResponse<ApiError> {
  return NextResponse.json(
    {
      error: status >= 500 ? "Server Error" : "Client Error",
      message,
      details,
    },
    { status }
  );
}
```

### 2. Type Your Responses

```typescript
interface Task {
  id: string;
  title: string;
  completed: boolean;
}

interface TasksResponse {
  tasks: Task[];
  total: number;
}

export async function GET(): Promise<NextResponse<TasksResponse>> {
  const tasks = await db.tasks.findMany();
  return NextResponse.json({ tasks, total: tasks.length });
}
```

### 3. Rate Limiting (Simple)

```typescript
const rateLimit = new Map<string, number[]>();

function isRateLimited(ip: string, limit = 10, window = 60000): boolean {
  const now = Date.now();
  const timestamps = rateLimit.get(ip) || [];

  // Remove old timestamps
  const recent = timestamps.filter((t) => now - t < window);
  recent.push(now);
  rateLimit.set(ip, recent);

  return recent.length > limit;
}

export async function POST(request: NextRequest) {
  const ip = request.ip || "unknown";

  if (isRateLimited(ip)) {
    return NextResponse.json(
      { error: "Too many requests" },
      { status: 429 }
    );
  }

  // Process request
}
```
