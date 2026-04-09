import { neon } from "@neondatabase/serverless"
import bcrypt from "bcryptjs"
import * as dotenv from "dotenv"
import * as path from "path"

// Load .env.local from web-form directory
dotenv.config({ path: path.resolve(process.cwd(), ".env.local") })

async function seed() {
  const databaseUrl = process.env.DATABASE_URL
  if (!databaseUrl) {
    console.error("❌ DATABASE_URL is not set in .env.local")
    process.exit(1)
  }

  const sql = neon(databaseUrl)

  const ADMIN_EMAIL = "admin@nexaflow.com"
  const ADMIN_PASSWORD = "Admin123!"
  const ADMIN_NAME = "NexaFlow Admin"

  // Check if admin already exists
  const existing = await sql`
    SELECT id FROM users WHERE email = ${ADMIN_EMAIL} LIMIT 1
  `

  if (existing.length > 0) {
    console.log("ℹ️  Admin user already exists — skipping")
    return
  }

  const hashedPassword = await bcrypt.hash(ADMIN_PASSWORD, 12)

  await sql`
    INSERT INTO users (name, email, hashed_password, role)
    VALUES (${ADMIN_NAME}, ${ADMIN_EMAIL}, ${hashedPassword}, 'admin')
  `

  console.log("✅ Admin user created: admin@nexaflow.com")
}

seed().catch((err) => {
  console.error("❌ Seed failed:", err)
  process.exit(1)
})
