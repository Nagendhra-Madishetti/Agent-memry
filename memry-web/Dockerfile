# Agent Memry web (Next.js). Build context = ./memry-web. NEXT_PUBLIC_* are build-time, so the
# API URL + demo bearer token are baked at build (the token is a low-privilege DEMO token).
# Node 22 + pnpm pinned to the lockfile's generator (v9 lockfile); corepack's latest pnpm needs
# Node 22 (node:sqlite), so both are pinned deliberately.
FROM node:22-slim AS deps
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-slim AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate
COPY --from=deps /app/node_modules ./node_modules
COPY . ./
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_API_TOKEN
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL NEXT_PUBLIC_API_TOKEN=$NEXT_PUBLIC_API_TOKEN
RUN pnpm build

FROM node:22-slim AS run
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
# Next standalone output: a minimal self-contained server + the static assets.
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
