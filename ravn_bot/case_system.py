from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands

from .config import MANAGEMENT_ROLE_NAMES, STAFF_ROLE_NAMES
from .embeds import RAVN_PURPLE, brand_embed, bot_avatar_url, ravn_embed

DB_PATH = Path(__file__).resolve().parent / "ravn.sqlite3"


def _db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS cases (
        case_id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        tribe TEXT NOT NULL,
        rule TEXT NOT NULL,
        punishment TEXT NOT NULL,
        issued_by INTEGER NOT NULL,
        issued_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        evidence TEXT DEFAULT ''
    )""")
    db.commit()
    return db


def _staff(member: discord.Member) -> bool:
    return member.guild_permissions.administrator or member.guild_permissions.manage_guild or any(r.name in STAFF_ROLE_NAMES for r in member.roles)


def _management(member: discord.Member) -> bool:
    return member.guild_permissions.administrator or any(r.name in MANAGEMENT_ROLE_NAMES for r in member.roles)


def create_case(guild_id: int, kind: str, tribe: str, rule: str, punishment: str, issued_by: int, evidence: str = "") -> int:
    db = _db()
    cur = db.execute(
        "INSERT INTO cases(guild_id,kind,tribe,rule,punishment,issued_by,issued_at,evidence) VALUES(?,?,?,?,?,?,?,?)",
        (guild_id, kind, tribe, rule, punishment, issued_by, datetime.now(timezone.utc).isoformat(), evidence),
    )
    db.commit()
    case_id = int(cur.lastrowid)
    db.close()
    return case_id


def register(bot: discord.Client) -> None:
    @bot.tree.command(name="punishments", description="View punishment history for a tribe.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def punishments(interaction: discord.Interaction, tribe: str) -> None:
        if not interaction.guild:
            return
        db = _db()
        rows = db.execute(
            "SELECT * FROM cases WHERE guild_id=? AND kind='punishment' AND lower(tribe)=lower(?) ORDER BY case_id DESC LIMIT 15",
            (interaction.guild.id, tribe),
        ).fetchall()
        db.close()
        embed = ravn_embed("⚖️ PUNISHMENT HISTORY", f"Records for **{tribe}**", colour=RAVN_PURPLE, footer="RAVN Server Manager • Case System")
        if not rows:
            embed.description += "\n\nNo punishment records found."
        else:
            for row in rows:
                status = "ACTIVE" if row["status"] == "active" else row["status"].upper()
                embed.add_field(
                    name=f"CASE-{row['case_id']:06d} • {status}",
                    value=f"📜 {row['rule']}\n🔨 {row['punishment']}\n👮 <@{row['issued_by']}> • <t:{int(datetime.fromisoformat(row['issued_at']).timestamp())}:R>",
                    inline=False,
                )
        await interaction.response.send_message(embed=brand_embed(embed, bot_avatar_url(interaction.client)), ephemeral=True)

    @bot.tree.command(name="punishment-remove", description="Void an existing punishment case.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def punishment_remove(interaction: discord.Interaction, case_number: int, reason: str) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member) or not _management(interaction.user):
            await interaction.response.send_message("Only management can void punishment cases.", ephemeral=True)
            return
        db = _db()
        cur = db.execute("UPDATE cases SET status=? WHERE guild_id=? AND case_id=? AND kind='punishment'", (f"voided: {reason}", interaction.guild.id, case_number))
        db.commit()
        db.close()
        if cur.rowcount == 0:
            await interaction.response.send_message(f"CASE-{case_number:06d} was not found.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ CASE-{case_number:06d} has been voided.", ephemeral=True)

    @bot.tree.command(name="appeal", description="Submit a punishment appeal to staff.")
    async def appeal(interaction: discord.Interaction, case_number: int, reason: str) -> None:
        if not interaction.guild:
            return
        channel = discord.utils.get(interaction.guild.text_channels, name="🛡️・STAFF REPORT TICKET")
        if not channel:
            await interaction.response.send_message("The staff report category is not configured.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"📩 Appeal submitted for **CASE-{case_number:06d}**. Please open a staff report ticket and provide your evidence.\n\n**Reason:** {reason}",
            ephemeral=True,
        )

    @bot.tree.command(name="report", description="Create a private player or tribe report.")
    async def report(interaction: discord.Interaction, player_or_tribe: str, category: str, details: str) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        category_channel = discord.utils.get(interaction.guild.categories, name="🚨・PLAYER REPORT TICKET")
        if not category_channel:
            await interaction.response.send_message("The 🚨・PLAYER REPORT TICKET category is missing.", ephemeral=True)
            return
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
        }
        for role in interaction.guild.roles:
            if role.name in STAFF_ROLE_NAMES:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)
        safe = "".join(ch for ch in player_or_tribe.lower() if ch.isalnum() or ch == "-")[:25] or "player"
        channel = await category_channel.create_text_channel(
            f"report-{safe}-{interaction.user.id}"[:100],
            overwrites=overwrites,
            topic=f"ravn_report;reporter:{interaction.user.id};state:open",
        )
        embed = ravn_embed("🚨 PLAYER REPORT", "Please upload screenshots/videos and any additional evidence in this private report channel.", colour=RAVN_PURPLE, footer="RAVN Server Manager • Reports")
        embed.add_field(name="Reported", value=player_or_tribe, inline=True)
        embed.add_field(name="Category", value=category, inline=True)
        embed.add_field(name="Details", value=details, inline=False)
        embed.add_field(name="Reporter", value=interaction.user.mention, inline=True)
        await channel.send(content=interaction.user.mention, embed=brand_embed(embed, bot_avatar_url(interaction.client)))
        await interaction.response.send_message(f"🚨 Report created: {channel.mention}. Upload your evidence there.", ephemeral=True)

    @bot.tree.command(name="case", description="View a RAVN case by case number.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def case(interaction: discord.Interaction, case_number: int) -> None:
        if not interaction.guild:
            return
        db = _db()
        row = db.execute("SELECT * FROM cases WHERE guild_id=? AND case_id=?", (interaction.guild.id, case_number)).fetchone()
        db.close()
        if not row:
            await interaction.response.send_message(f"CASE-{case_number:06d} was not found.", ephemeral=True)
            return
        embed = ravn_embed(f"📋 CASE-{case_number:06d}", f"**{row['kind'].title()} case**", colour=RAVN_PURPLE, footer="RAVN Server Manager • Case System")
        embed.add_field(name="🏹 Tribe / Player", value=row["tribe"], inline=True)
        embed.add_field(name="📜 Rule", value=row["rule"], inline=True)
        embed.add_field(name="🔨 Action", value=row["punishment"], inline=False)
        embed.add_field(name="👮 Issued By", value=f"<@{row['issued_by']}>", inline=True)
        embed.add_field(name="📌 Status", value=row["status"].upper(), inline=True)
        await interaction.response.send_message(embed=brand_embed(embed, bot_avatar_url(interaction.client)), ephemeral=True)
