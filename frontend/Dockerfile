# Frontend Dockerfile for Next.js
# Development and production multi-stage build

FROM node:20-alpine AS base
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Development stage
FROM base AS dev
COPY package.json ./
RUN npm install
# Don't copy source - will be mounted as volume
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["npm", "run", "dev"]

# Dependencies stage for production
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm install --production=false

# Builder stage
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Production runner
FROM base AS runner
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Copy standalone output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
