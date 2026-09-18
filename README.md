# RAVN Server Manager

RAVN Server Manager is a Python `discord.py` bot for ARK Survival Ascended PvP communities.

## What it includes

- Idempotent `/setup-server` provisioning for roles, categories, channels, permissions, and starter embeds
- Private button-based support tickets with claim, close, delete, and transcript logging
- `/warn`, `/kick`, `/ban`, `/timeout`, `/clear`, and `/unban` moderation commands
- `/recruit` modal for structured tribe recruitment posts
- `/patchnotes`, `/giveaway`, `/event`, and `/announce` staff tools
- Environment-based configuration and structured logging

## Configuration

Required secret:

```text
DISCORD_TOKEN
```

Optional environment variables:

```text
DISCORD_GUILD_ID=123456789012345678
LOG_LEVEL=INFO
```

When `DISCORD_GUILD_ID` is provided, slash commands sync to that guild immediately. Without it, commands sync globally and Discord may take time to propagate them.

The bot needs the Discord `Server Members Intent` enabled and should be invited with the `bot` and `applications.commands` scopes. Give it Manage Server, Manage Channels, Manage Roles, Manage Messages, Moderate Members, Kick Members, Ban Members, and View Audit Log as appropriate. Its role must sit above roles it needs to manage.

## Run

```bash
python run_bot.py
```

Run `/setup-server` once as a server administrator. Running it again repairs missing objects without duplicating existing roles, categories, channels, or starter embeds.