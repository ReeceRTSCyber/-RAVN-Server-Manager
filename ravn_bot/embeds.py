from __future__ import annotations

from datetime import datetime, timezone

import discord


ARK_BLUE = discord.Colour.from_rgb(20, 91, 140)
ARK_DARK_BLUE = discord.Colour.from_rgb(10, 39, 64)
SUCCESS = discord.Colour.from_rgb(45, 175, 105)
WARNING = discord.Colour.from_rgb(220, 145, 42)
DANGER = discord.Colour.from_rgb(190, 55, 65)


def ravn_embed(
    title: str,
    description: str | None = None,
    *,
    colour: discord.Colour = ARK_BLUE,
    footer: str = "RAVN Server Manager",
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        colour=colour,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=footer)
    return embed


def brand_embed(embed: discord.Embed, image_url: str | None) -> discord.Embed:
    """Add the RAVN artwork as a Discord-renderable embed thumbnail."""
    if image_url:
        embed.set_thumbnail(url=image_url)
    return embed


def bot_avatar_url(client: discord.Client) -> str | None:
    """Return the configured bot avatar URL, which Discord can fetch directly."""
    return str(client.user.display_avatar.url) if client.user else None


def rules_embed() -> discord.Embed:
    embed = ravn_embed(
        "📜 RAVN Server Rules",
        "Play hard, play fair, and protect the community that makes the wipe worth showing up for.",
        colour=ARK_DARK_BLUE,
    )
    embed.add_field(
        name="1. Respect the community",
        value="No harassment, hate speech, threats, spam, or deliberate disruption.",
        inline=False,
    )
    embed.add_field(
        name="2. Keep PvP in-game",
        value="Competitive banter is fine. Personal attacks, doxxing, and targeted abuse are not.",
        inline=False,
    )
    embed.add_field(
        name="3. Trade honestly",
        value="Use the vouch system, record agreements, and report suspected scams promptly.",
        inline=False,
    )
    embed.add_field(
        name="4. Follow staff direction",
        value="Appeals belong in support tickets. Do not argue moderation actions in public channels.",
        inline=False,
    )
    embed.add_field(
        name="5. Protect server information",
        value="Do not share private coordinates, staff logs, or ticket content outside the intended audience.",
        inline=False,
    )
    return embed


def server_info_embed(guild: discord.Guild) -> discord.Embed:
    embed = ravn_embed(
        "📌 RAVN Server Information",
        "Welcome to RAVN, an ARK Survival Ascended PvP community built around organised tribes and active competition.",
    )
    embed.add_field(name="Server", value=guild.name, inline=True)
    embed.add_field(name="Members", value=str(guild.member_count or 0), inline=True)
    embed.add_field(name="Platform", value="PC • Xbox • PlayStation", inline=True)
    embed.add_field(
        name="Start here",
        value="Read the rules, choose notification roles, then introduce yourself in the community.",
        inline=False,
    )
    return embed


def welcome_embed(member: discord.Member) -> discord.Embed:
    return ravn_embed(
        f"Welcome to RAVN, {member.display_name}",
        "You are now part of a competitive ARK community. Read the rules, select your roles, and find your tribe.",
        colour=SUCCESS,
    )


def role_selection_embed() -> discord.Embed:
    embed = ravn_embed(
        "🎭 Choose Your Roles",
        "Select one platform and any notification roles you want. Changing a selection automatically "
        "adds and removes only the self-assignable roles below.",
    )
    embed.add_field(
        name="Platform",
        value="Choose one: 🎮 PC, 🎮 Xbox, or 🎮 PlayStation.",
        inline=False,
    )
    embed.add_field(
        name="Notifications",
        value="Choose any: 📢 Announcements, ⚔️ PvP, 💀 Raids, 🦖 Bosses, 💰 Trading, or 🎉 Events.",
        inline=False,
    )
    return embed


def recruitment_embed() -> discord.Embed:
    return ravn_embed(
        "🏹 Tribe Recruitment",
        "Use `/recruit` to publish a structured tribe recruitment post. Include accurate requirements and a reliable way to reach you.",
    )


def trading_rules_embed() -> discord.Embed:
    embed = ravn_embed(
        "💰 Trading Rules",
        "Keep trades clear, fair, and traceable.",
        colour=WARNING,
    )
    embed.add_field(
        name="Before trading",
        value="Confirm the item, quantity, server, and hand-off location in writing.",
        inline=False,
    )
    embed.add_field(
        name="After trading",
        value="Leave a vouch only when the trade is complete. Report suspected scams through a ticket.",
        inline=False,
    )
    return embed


def ticket_info_embed() -> discord.Embed:
    return ravn_embed(
        "🎫 RAVN SUPPORT CENTRE",
        "Choose the ticket type that best matches your request, then complete the required form "
        "with your name, map/server, and reason before a private ticket is created.",
    )


def reports_embed() -> discord.Embed:
    return ravn_embed(
        "🚨 Player Reports",
        "Open a Player Report ticket with the player name, server/map, approximate time, and any evidence you have.",
        colour=DANGER,
    )


def announcements_embed(title: str, body: str) -> discord.Embed:
    return ravn_embed(f"📢 {title}", body, colour=ARK_DARK_BLUE)


def wipe_info_embed() -> discord.Embed:
    return ravn_embed(
        "📅 Wipe Information",
        "Wipe details will be posted here by the management team. Follow the announcements role so you do not miss schedule changes.",
        colour=ARK_DARK_BLUE,
    )


def patch_notes_embed(version: str, changes: str) -> discord.Embed:
    return ravn_embed(
        f"📝 Patch Notes — {version}",
        changes,
        colour=ARK_DARK_BLUE,
        footer="RAVN Server Manager • Server Updates",
    )


def event_embed(
    name: str,
    date: str,
    time: str,
    description: str,
    prize: str,
    location: str,
    requirements: str,
) -> discord.Embed:
    embed = ravn_embed(f"🎉 {name}", description, colour=SUCCESS)
    embed.add_field(name="Date", value=date, inline=True)
    embed.add_field(name="Time", value=time, inline=True)
    embed.add_field(name="Prize", value=prize or "TBA", inline=True)
    embed.add_field(name="Location", value=location or "TBA", inline=True)
    embed.add_field(name="Requirements", value=requirements or "None", inline=False)
    return embed
