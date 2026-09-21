from __future__ import annotations

import os
from dataclasses import dataclass


ROLE_GROUPS: dict[str, list[str]] = {
    "SERVER MANAGEMENT": [
        "👑 Owner",
        "🛡️ Co-Owner",
        "⚡ Server Manager",
        "🔧 Head Admin",
        "🛡️ Admin",
        "🔨 Moderator",
        "🧹 Trial Moderator",
        "🤖 Bot",
    ],
    "COMMUNITY": [
        "💎 Server Booster",
        "🏆 Veteran",
        "⭐ Member",
        "🆕 New Member",
        "🔥 Active PvPer",
        "💤 Inactive",
    ],
    "TRIBE": [
        "👑 Tribe Leader",
        "⚔️ Tribe Admin",
        "🛡️ Tribe Member",
        "🔫 PvPer",
        "🏗️ Builder",
        "🧬 Breeder",
        "🦖 Tamer",
    ],
    "OTHER": ["📥 Recruiter", "🎮 PS5", "🖥️ PC", "🟢 Xbox"],
    "REGION ROLES": ["🇩🇪 Europe", "🌎 NA", "🇬🇧 UK", "🇦🇺 AUS"],
    "PING ROLES": [
        "📣 Small Announcements",
        "🎉 Giveaway Ping",
        "🔄 Rollback Ping",
        "♻️ Restart Ping",
        "🦖 Event Dino Ping",
        "🔻 Event Crate Ping",
        "🪨 Golem Ping",
        "🚀 Events Ping",
        "🎉 Discord Event Ping",
    ],
    # Keep the original notification roles available for existing members and
    # automations, even though the current self-assign panel uses PING ROLES.
    "LEGACY NOTIFICATION ROLES": [
        "📢 Announcements",
        "⚔️ PvP",
        "💀 Raids",
        "🦖 Bosses",
        "💰 Trading",
        "🎉 Events",
    ],
}

ROLE_NAMES = [role for group in ROLE_GROUPS.values() for role in group]
PLATFORM_ROLE_NAMES = ["🎮 PS5", "🖥️ PC", "🟢 Xbox"]
REGION_ROLE_NAMES = ["🇩🇪 Europe", "🌎 NA", "🇬🇧 UK", "🇦🇺 AUS"]
PING_ROLE_NAMES = [
    "📣 Small Announcements",
    "🎉 Giveaway Ping",
    "🔄 Rollback Ping",
    "♻️ Restart Ping",
    "🦖 Event Dino Ping",
    "🔻 Event Crate Ping",
    "🪨 Golem Ping",
    "🚀 Events Ping",
    "🎉 Discord Event Ping",
]
NOTIFICATION_ROLE_NAMES = PING_ROLE_NAMES

CATEGORY_CHANNELS: dict[str, list[str]] = {
    "📜 INFORMATION": [
        "📜・server-rules",
        "📢・announcements",
        "📌・server-info",
        "🗺️・server-maps",
        "📅・wipe-info",
        "🔗・important-links",
        "🎭・role-selection",
    ],
    "💬 COMMUNITY": [
        "💬・general",
        "👋・introductions",
        "📸・media",
        "🎥・content-creators",
        "😂・memes",
        "💡・suggestions",
        "🗳️・polls",
        "🤖・bot-commands",
    ],
    "🏹 TRIBE RECRUITMENT": [
        "📢・tribe-recruitment",
        "🔎・looking-for-tribe",
        "👥・looking-for-players",
        "📝・recruitment-applications",
        "📊・tribe-stats",
    ],
    "💰 TRADING": [
        "💰・trade-chat",
        "🏷️・trade-vouches",
    ],
    "🎫・SUPPORT TICKETS": ["🎫・create-ticket"],
    "🚨・PLAYER REPORT TICKET": [],
    "🛡️・STAFF REPORT TICKET": [],
    "💰・DONATION TICKET": [],
    "🔧・TECHNICAL SUPPORT TICKET": [],
    "🔒 STAFF": [
        "💬・staff-chat",
        "📋・staff-tasks",
        "🚨・reports",
        "🔨・punishments",
        "📜・mod-logs",
        "📊・staff-logs",
        "🎫・ticket-logs",
    ],
    "👑 MANAGEMENT": [
        "👑・owner-chat",
        "📢・management",
        "🧠・development",
        "🔧・server-development",
        "📊・server-statistics",
        "📝・change-log",
    ],
}

VOICE_CATEGORIES: dict[str, list[str]] = {
    "🔊 COMMUNITY VOICE": [
        "🔊・General 1",
        "🔊・General 2",
        "🔊・General 3",
        "🎮・Gaming 1",
        "🎮・Gaming 2",
        "🎮・Gaming 3",
    ],
    "🎵 OTHER VOICE": ["🎵・Music", "💤・AFK"],
}

PRIVATE_CATEGORIES = {"🔒 STAFF", "👑 MANAGEMENT"}
INFO_CHANNELS = {"📜 INFORMATION"}

# Retired layout objects are removed by the next administrator-run /setup-server.
REMOVED_CATEGORIES = {
    "🎫 SUPPORT",
    "⚔️ ARK PVP",
    "🧬 BREEDING",
    "💀 BOSSES & PROGRESSION",
    "🏰 FOB & RAID ORGANISATION",
    "⚔️ PVP VOICE",
    "👥 TRIBES VOICE",
}
REMOVED_CHANNELS = {
    "🎫 SUPPORT": set(),
    "💰 TRADING": {
        "🦖・dino-trading",
        "🧬・mutations",
        "🔫・weapon-trading",
        "🛡️・armour-trading",
        "💎・resource-trading",
        "🚨・trade-alerts",
    },
    "🏹 TRIBE RECRUITMENT": {"🏆・tribe-rosters"},
}


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int | None
    log_level: str


def load_settings() -> Settings:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN is required. Add it as a Replit Secret.")

    raw_guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
    guild_id = int(raw_guild_id) if raw_guild_id.isdigit() else None
    return Settings(
        token=token,
        guild_id=guild_id,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )


def role_name(base_name: str) -> str:
    return base_name


STAFF_ROLE_NAMES = {
    "🔧 Head Admin",
    "🛡️ Admin",
    "🔨 Moderator",
    "🧹 Trial Moderator",
    "⚡ Server Manager",
    "🛡️ Co-Owner",
    "👑 Owner",
}

MANAGEMENT_ROLE_NAMES = {"⚡ Server Manager", "🛡️ Co-Owner", "👑 Owner"}
TRIBE_ROLE_NAMES = {
    "👑 Tribe Leader",
    "⚔️ Tribe Admin",
    "🛡️ Tribe Member",
    "🔫 PvPer",
    "🏗️ Builder",
    "🧬 Breeder",
    "🦖 Tamer",
}
