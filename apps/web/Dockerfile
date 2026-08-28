FROM node:22-alpine AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/package.json apps/web/package-lock.json ./
COPY apps/web/tsconfig.json apps/web/next.config.ts apps/web/postcss.config.mjs ./
COPY apps/web/app ./app
COPY apps/web/components ./components
COPY apps/web/lib ./lib
COPY apps/web/public ./public
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
