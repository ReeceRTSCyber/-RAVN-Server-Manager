---
name: Discord embed assets
description: Reliable image rendering for Discord embeds sent or updated by the bot.
---

Use `attachment://filename` for project-owned artwork and include a fresh `discord.File` when creating or editing the message. Discord converts it to a CDN URL after delivery. Use the live bot avatar URL for dynamic embeds when a separate upload is unnecessary.

**Why:** Discord cannot fetch local filesystem paths, and an attachment reference without the file upload renders as a broken image. Message edits replace attachments, so the file must be supplied again.

**How to apply:** Seed branded panels with a stable attachment filename and reattach the asset on every edit; use `client.user.display_avatar.url` for ordinary runtime-generated embeds.