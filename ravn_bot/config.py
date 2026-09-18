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
    "OTHER": ["📥 Recruiter", "🎮 PC", "🎮 Xbox", "🎮 PlayStation"],
    "NOTIFICATION ROLES": [
        "📢 Announcements",
        "⚔️ PvP",
        "💀 Raids",
        "🦖 Bosses",
        "💰 Trading",
        "🎉 Events",
    ],
}

ROLE_NAMES = [role for group in ROLE_GROUPS.values() for role in group]
PLATFORM_ROLE_NAMES = ["🎮 PC", "🎮 Xbox", "🎮 PlayStation"]
NOTIFICATION_ROLE_NAMES = [
    "📢 Announcements",
    "⚔️ PvP",
    "💀 Raids",
    "🦖 Bosses",
    "💰 Trading",
    "🎉 Events",
]

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
    "⚔️ ARK PVP": [
        "🔥・pvp-chat",
        "⚔️・war-room",
        "🚨・raid-alerts",
        "💀・raid-reports",
        "🏰・base-showcase",
        "🧱・base-designs",
        "🔫・weapon-loadouts",
        "🦖・dino-meta",
        "💣・raid-meta",
        "🛡️・defence",
    ],
    "🏹 TRIBE RECRUITMENT": [
        "📢・tribe-recruitment",
        "🔎・looking-for-tribe",
        "👥・looking-for-players",
        "📝・recruitment-applications",
        "🏆・tribe-rosters",
        "📊・tribe-stats",
    ],
    "💰 TRADING": [
        "💰・trade-chat",
        "🦖・dino-trading",
        "🧬・mutations",
        "🔫・weapon-trading",
        "🛡️・armour-trading",
        "💎・resource-trading",
        "🏷️・trade-vouches",
        "🚨・trade-alerts",
    ],
    "🧬 BREEDING": [
        "🧬・breeding-chat",
        "🥚・egg-trading",
        "🧬・mutation-lines",
        "📊・stat-checks",
        "🦖・dino-lines",
        "🏆・top-lines",
    ],
    "💀 BOSSES & PROGRESSION": [
        "🦖・boss-chat",
        "⚔️・boss-teams",
        "🗺️・artifact-locations",
        "🦴・tribute-farming",
        "🏆・ascension",
    ],
    "🏰 FOB & RAID ORGANISATION": [
        "📍・fob-coordinates",
        "🏗️・fob-builds",
        "🛡️・fob-defence",
        "🚀・raid-planning",
        "💣・raid-targets",
        "📋・raid-checklists",
        "🏆・raid-results",
    ],
    "🎫 SUPPORT": [
        "🎫・create-ticket",
        "🚨・player-report",
        "🛡️・staff-report",
        "💰・donation-support",
        "🔧・technical-support",
    ],
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
    "⚔️ PVP VOICE": [
        "⚔️・PvP 1",
        "⚔️・PvP 2",
        "💀・Raid Room 1",
        "💀・Raid Room 2",
        "🏗️・FOB Room",
        "🛡️・Defence Room",
    ],
    "👥 TRIBES VOICE": [
        "👑・Tribe Leaders",
        "🔥・Tribe 1",
        "🔥・Tribe 2",
        "🔥・Tribe 3",
        "🔥・Tribe 4",
    ],
    "🎵 OTHER VOICE": ["🎵・Music", "💤・AFK"],
}

PRIVATE_CATEGORIES = {"🔒 STAFF", "👑 MANAGEMENT"}
INFO_CHANNELS = {"📜 INFORMATION"}


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
