import { neon } from "@neondatabase/serverless"

export interface DbUser {
  id: string
  name: string
  email: string
  hashed_password: string
  role: "admin" | "agent"
  created_at: string
}

function getDb() {
  const url = process.env.DATABASE_URL
  if (!url) throw new Error("DATABASE_URL is not set")
  return neon(url)
}

export async function getUserByEmail(email: string): Promise<DbUser | null> {
  const sql = getDb()
  const rows = await sql`
    SELECT id, name, email, hashed_password, role, created_at
    FROM users
    WHERE email = ${email.toLowerCase()}
    LIMIT 1
  `
  if (rows.length === 0) return null
  return rows[0] as DbUser
}

export async function createUser(
  name: string,
  email: string,
  hashedPassword: string,
  role: "admin" | "agent"
): Promise<Omit<DbUser, "hashed_password">> {
  const sql = getDb()
  const rows = await sql`
    INSERT INTO users (name, email, hashed_password, role)
    VALUES (${name}, ${email.toLowerCase()}, ${hashedPassword}, ${role})
    RETURNING id, name, email, role, created_at
  `
  return rows[0] as Omit<DbUser, "hashed_password">
}
