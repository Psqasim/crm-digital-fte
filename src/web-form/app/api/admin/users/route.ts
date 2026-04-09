import { auth } from "@/auth"
import { createUser } from "@/lib/db"
import { z } from "zod"
import bcrypt from "bcryptjs"

const createUserSchema = z.object({
  name: z.string().min(2).max(255),
  email: z.string().email(),
  password: z.string().min(8),
  role: z.enum(["admin", "agent"]),
})

export async function POST(req: Request) {
  // Step 1: Auth check
  const session = await auth()
  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 })
  }

  // Step 2: Role check — only session role is trusted, never request body
  if (session.user.role !== "admin") {
    return Response.json({ error: "Forbidden — admin role required" }, { status: 403 })
  }

  // Step 3: Validate body
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  const parsed = createUserSchema.safeParse(body)
  if (!parsed.success) {
    return Response.json(
      { error: "Validation failed", details: parsed.error.issues },
      { status: 400 }
    )
  }

  // Step 4: Hash password
  const hashedPassword = await bcrypt.hash(parsed.data.password, 12)

  // Step 5: Insert user
  try {
    const user = await createUser(
      parsed.data.name,
      parsed.data.email,
      hashedPassword,
      parsed.data.role
    )
    return Response.json(user, { status: 201 })
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    if (message.toLowerCase().includes("unique") || message.toLowerCase().includes("duplicate")) {
      return Response.json(
        { error: "A user with this email address already exists" },
        { status: 409 }
      )
    }
    console.error("create_user failed:", message)
    return Response.json({ error: "Failed to create user" }, { status: 500 })
  }
}
