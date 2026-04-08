# Stage 1: builder — build Next.js standalone output
FROM node:20-alpine AS builder
WORKDIR /app
COPY src/web-form/package*.json ./
RUN npm ci
COPY src/web-form/ .
RUN npm run build

# Stage 2: runtime — minimal production image
FROM node:20-alpine
WORKDIR /app

# Copy standalone output (includes node_modules trace)
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
