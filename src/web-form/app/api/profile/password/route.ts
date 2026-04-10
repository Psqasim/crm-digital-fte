import { auth } from "@/auth"
import { getUserByEmail } from "@/lib/db"
import { z } from "zod"
import bcrypt from "bcryptjs"
import { neon } from "@neondatabase/serverless"

const schema = z.object({
  currentPassword: z.string().min(1),
  newPassword: z.string().min(8),
})

export async function POST(req: Request) {
  const session = await auth()
  if (!session) return Response.json({ error: "Unauthorized" }, { status: 401 })

  const body = await req.json().catch(() => null)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return Response.json({ error: "Invalid request" }, { status: 400 })

  const user = await getUserByEmail(session.user.email!)
  if (!user) return Response.json({ error: "User not found" }, { status: 404 })

  const passwordMatch = await bcrypt.compare(parsed.data.currentPassword, user.hashed_password)
  if (!passwordMatch) return Response.json({ error: "Current password is incorrect" }, { status: 400 })

  const hashedNew = await bcrypt.hash(parsed.data.newPassword, 12)

  const sql = neon(process.env.DATABASE_URL!)
  await sql`UPDATE users SET hashed_password = ${hashedNew} WHERE email = ${session.user.email!.toLowerCase()}`

  return Response.json({ message: "Password updated" }, { status: 200 })
}
