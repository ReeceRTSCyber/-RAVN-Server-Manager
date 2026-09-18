from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

import discord

from .embeds import (
    ARK_BLUE,
    SUCCESS,
    announcements_embed,
    event_embed,
    patch_notes_embed,
    recruitment_embed,
    ravn_embed,
)
from .tickets import _is_staff

logger = logging.getLogger(__name__)


def _find_channel(guild: discord.Guild, name: str) -> discord.TextChannel | None:
    return discord.utils.get(guild.text_channels, name=name)


class RecruitmentModal(discord.ui.Modal, title="Tribe Recruitment Application"):
    tribe_name = discord.ui.TextInput(label="Tribe name", max_length=80)
    platform = discord.ui.TextInput(label="Platform", placeholder="PC, Xbox, PlayStation, or crossplay", max_length=60)
    server_map = discord.ui.TextInput(label="Server / map", max_length=120)
    player_requirements = discord.ui.TextInput(
        label="Player requirements",
        style=discord.TextStyle.paragraph,
        max_length=800,
    )
    tribe_requirements = discord.ui.TextInput(
        label="Tribe requirements and contact",
        style=discord.TextStyle.paragraph,
        placeholder="What are you looking for? How should players contact you?",
        max_length=800,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        channel = _find_channel(interaction.guild, "📢・tribe-recruitment") or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("A recruitment channel is not available.", ephemeral=True)
            return
        embed = ravn_embed(
            f"🏹 {self.tribe_name.value}",
            f"Posted by {interaction.user.mention}",
            colour=ARK_BLUE,
        )
        embed.add_field(name="Platform", value=self.platform.value, inline=True)
        embed.add_field(name="Server / map", value=self.server_map.value, inline=True)
        embed.add_field(name="Player requirements", value=self.player_requirements.value, inline=False)
        embed.add_field(name="Tribe requirements / contact", value=self.tribe_requirements.value, inline=False)
        await channel.send(embed=embed)
        await interaction.response.send_message(f"Your recruitment post is live in {channel.mention}.", ephemeral=True)


class GiveawayView(discord.ui.View):
    def __init__(self, prize: str, winners: int, ends_at: float) -> None:
        super().__init__(timeout=None)
        self.prize = prize
        self.winners = winners
        self.ends_at = ends_at
        self.entries: set[int] = set()
        self.message: discord.Message | None = None

    @discord.ui.button(label="Enter giveaway", emoji="🎉", style=discord.ButtonStyle.success, custom_id="ravn:giveaway:enter")
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.entries.add(interaction.user.id)
        await interaction.response.send_message("You are entered. Good luck.", ephemeral=True)

    async def finish(self) -> None:
        delay = max(0, self.ends_at - datetime.now(timezone.utc).timestamp())
        await asyncio.sleep(delay)
        if not self.message:
            return
        winners = random.sample(list(self.entries), k=min(self.winners, len(self.entries)))
        if winners:
            mentions = ", ".join(f"<@{winner}>" for winner in winners)
            description = f"Congratulations {mentions}.\n\nPrize: **{self.prize}**"
        else:
            description = f"No valid entries were recorded.\n\nPrize: **{self.prize}**"
        try:
            await self.message.edit(
                embed=ravn_embed("🎉 Giveaway ended", description, colour=SUCCESS),
                view=None,
            )
        except discord.HTTPException:
            logger.warning("Could not finish giveaway message %s", self.message.id)


def register(bot: discord.Client) -> None:
    @bot.tree.command(name="recruit", description="Open a form to publish a tribe recruitment post.")
    async def recruit(interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(RecruitmentModal())

    @bot.tree.command(name="patchnotes", description="Publish server patch notes to the change log.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def patchnotes(interaction: discord.Interaction, version: str, changes: str) -> None:
        if not interaction.guild:
            return
        channel = _find_channel(interaction.guild, "📝・change-log")
        if not channel:
            await interaction.response.send_message("The change log channel does not exist yet. Run `/setup-server` first.", ephemeral=True)
            return
        await channel.send(embed=patch_notes_embed(version, changes))
        await interaction.response.send_message(f"Patch notes posted in {channel.mention}.", ephemeral=True)

    @bot.tree.command(name="giveaway", description="Start a giveaway with a button to enter.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(
        interaction: discord.Interaction,
        prize: str,
        duration_minutes: discord.app_commands.Range[int, 1, 10080],
        winners: discord.app_commands.Range[int, 1, 20],
    ) -> None:
        ends_at = datetime.now(timezone.utc).timestamp() + duration_minutes * 60
        view = GiveawayView(prize, winners, ends_at)
        embed = ravn_embed(
            "🎉 Giveaway",
            f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(ends_at)}:R>\n\nPress the button below to enter.",
            colour=SUCCESS,
        )
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        asyncio.create_task(view.finish())

    @bot.tree.command(name="event", description="Publish a RAVN community event announcement.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def event(
        interaction: discord.Interaction,
        name: str,
        date: str,
        time: str,
        description: str,
        prize: str = "TBA",
        location: str = "TBA",
        requirements: str = "None",
    ) -> None:
        if not interaction.guild:
            return
        channel = _find_channel(interaction.guild, "📢・announcements") or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return
        await channel.send(embed=event_embed(name, date, time, description, prize, location, requirements))
        await interaction.response.send_message(f"Event posted in {channel.mention}.", ephemeral=True)

    @bot.tree.command(name="announce", description="Publish a staff announcement.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def announce(interaction: discord.Interaction, title: str, body: str) -> None:
        if not interaction.guild:
            return
        channel = _find_channel(interaction.guild, "📢・announcements") or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return
        await channel.send(embed=announcements_embed(title, body))
        await interaction.response.send_message(f"Announcement posted in {channel.mention}.", ephemeral=True)
