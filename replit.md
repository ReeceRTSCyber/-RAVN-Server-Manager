# RAVN Server Manager

An administrator-friendly Discord bot that provisions and operates ARK Survival Ascended PvP communities.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string
- `python run_bot.py` — run the Discord bot
- Required secret: `DISCORD_TOKEN`
- Optional env: `DISCORD_GUILD_ID` for immediate guild-scoped slash-command sync

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `ravn_bot/config.py` — roles, categories, channels, and environment configuration
- `ravn_bot/setup_server.py` — idempotent server provisioning and starter embeds
- `ravn_bot/tickets.py` — persistent ticket panel and transcript workflow
- `ravn_bot/moderation.py` — moderation commands and logs
- `ravn_bot/features.py` — recruitment, patch notes, giveaways, events, and announcements
- `ravn_bot/main.py` — bot startup, command sync, and lifecycle events

## Architecture decisions

- The bot uses slash commands only; its message content intent is not required.
- `DISCORD_GUILD_ID` is optional so the same code supports immediate development sync and global production sync.
- Setup matches existing objects by exact names and seeds each starter embed only once using the RAVN footer marker.
- Ticket controls are persistent views with stable custom IDs, so they continue working after a bot restart.

## Product

RAVN Server Manager provisions a complete ARK PvP Discord server and provides private support tickets, moderation, recruitment forms, patch notes, giveaways, events, and announcements.

## User preferences

 - Keep the Discord token in Replit Secrets under `DISCORD_TOKEN`; never hard-code it.

## Gotchas

- The bot role must be above the roles it creates or manages in Discord's hierarchy.
- Enable the Server Members Intent in the Discord Developer Portal before relying on member join welcomes.

## Pointers

- See the `pnpm-workspace` skill for the existing TypeScript workspace.
- See `README.md` for RAVN setup and Discord permissions.
