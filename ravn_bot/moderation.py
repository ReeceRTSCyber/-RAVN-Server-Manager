from __future__ import annotations

import logging
from datetime import timedelta

import discord

from .config import STAFF_ROLE_NAMES
from .embeds import DANGER, WARNING, ravn_embed

logger = logging.getLogger(__name__)


def _mod_log(guild: discord.Guild) -> discord.TextChannel | None:
    return discord.utils.get(guild.text_channels, name="📜・mod-logs")


async def log_action(
    guild: discord.Guild,
    action: str,
    moderator: discord.Member,
    target: discord.abc.User | discord.Member | str,
    reason: str,
) -> None:
    channel = _mod_log(guild)
    if not channel:
        return
    target_text = target.mention if isinstance(target, discord.Member) else str(target)
    await channel.send(
        embed=ravn_embed(
            f"🛡️ {action}",
            f"**Target:** {target_text}\n**Moderator:** {moderator.mention}\n**Reason:** {reason}",
            colour=DANGER if action in {"Ban", "Kick", "Timeout"} else WARNING,
            footer="RAVN Moderation Logs",
        )
    )


def _can_moderate(member: discord.Member, target: discord.Member) -> bool:
    if target == member or target.guild_permissions.administrator:
        return False
    return member.top_role > target.top_role


def register(bot: discord.Client) -> None:
    @bot.tree.command(name="warn", description="Warn a member and log the action.")
    @discord.app_commands.default_permissions(moderate_members=True)
    @discord.app_commands.checks.has_permissions(moderate_members=True)
    async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not _can_moderate(interaction.user, member):
            await interaction.response.send_message("You cannot moderate that member.", ephemeral=True)
            return
        try:
            await member.send(f"You have been warned in **{interaction.guild.name}**: {reason}")
        except discord.HTTPException:
            pass
        await log_action(interaction.guild, "Warning", interaction.user, member, reason)
        await interaction.response.send_message(f"{member.mention} has been warned.", ephemeral=True)

    @bot.tree.command(name="kick", description="Kick a member and log the action.")
    @discord.app_commands.default_permissions(kick_members=True)
    @discord.app_commands.checks.has_permissions(kick_members=True)
    async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not _can_moderate(interaction.user, member):
            await interaction.response.send_message("You cannot moderate that member.", ephemeral=True)
            return
        await member.kick(reason=reason)
        await log_action(interaction.guild, "Kick", interaction.user, member, reason)
        await interaction.response.send_message(f"{member} was kicked.", ephemeral=True)

    @bot.tree.command(name="ban", description="Ban a member and log the action.")
    @discord.app_commands.default_permissions(ban_members=True)
    @discord.app_commands.checks.has_permissions(ban_members=True)
    async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not _can_moderate(interaction.user, member):
            await interaction.response.send_message("You cannot moderate that member.", ephemeral=True)
            return
        await member.ban(reason=reason, delete_message_seconds=0)
        await log_action(interaction.guild, "Ban", interaction.user, member, reason)
        await interaction.response.send_message(f"{member} was banned.", ephemeral=True)

    @bot.tree.command(name="timeout", description="Timeout a member for a number of minutes.")
    @discord.app_commands.default_permissions(moderate_members=True)
    @discord.app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: discord.app_commands.Range[int, 1, 40320],
        reason: str = "No reason provided",
    ) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not _can_moderate(interaction.user, member):
            await interaction.response.send_message("You cannot moderate that member.", ephemeral=True)
            return
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await log_action(interaction.guild, "Timeout", interaction.user, member, f"{minutes} minutes — {reason}")
        await interaction.response.send_message(f"{member.mention} was timed out for {minutes} minutes.", ephemeral=True)

    @bot.tree.command(name="clear", description="Delete recent messages from this channel.")
    @discord.app_commands.default_permissions(manage_messages=True)
    @discord.app_commands.checks.has_permissions(manage_messages=True)
    async def clear(
        interaction: discord.Interaction,
        amount: discord.app_commands.Range[int, 1, 100],
    ) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

    @bot.tree.command(name="unban", description="Unban a user by their Discord ID.")
    @discord.app_commands.default_permissions(ban_members=True)
    @discord.app_commands.checks.has_permissions(ban_members=True)
    async def unban(interaction: discord.Interaction, user_id: str) -> None:
        if not interaction.guild:
            return
        try:
            user = await bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=f"Unbanned by {interaction.user}")
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("No banned user was found with that ID.", ephemeral=True)
            return
        await log_action(interaction.guild, "Unban", interaction.user, user, "Manual unban")
        await interaction.response.send_message(f"{user} was unbanned.", ephemeral=True)
