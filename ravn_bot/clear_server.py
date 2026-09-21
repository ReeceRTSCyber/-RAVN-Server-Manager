from __future__ import annotations

import logging
from dataclasses import dataclass

import discord

from .embeds import DANGER, SUCCESS, ravn_embed

logger = logging.getLogger(__name__)


@dataclass
class DeletionResult:
    channels_deleted: int = 0
    categories_deleted: int = 0
    failures: int = 0


def _is_server_owner(interaction: discord.Interaction) -> bool:
    return bool(interaction.guild and interaction.guild.owner_id == interaction.user.id)


async def _delete_managed_channels(guild: discord.Guild) -> DeletionResult:
    result = DeletionResult()
    bot_member = guild.me
    if not bot_member:
        result.failures = 1
        logger.error("Cannot clear guild %s because the bot member is unavailable", guild.id)
        return result

    # Delete child channels first, then categories. Roles, the guild itself,
    # and the bot's role are intentionally never touched by this operation.
    channels = [channel for channel in guild.channels if not isinstance(channel, discord.CategoryChannel)]
    categories = [channel for channel in guild.categories]

    for channel in channels:
        try:
            if not channel.permissions_for(bot_member).manage_channels:
                continue
            await channel.delete(reason="RAVN /clear-server confirmed by an authorized administrator")
            result.channels_deleted += 1
        except discord.Forbidden:
            result.failures += 1
            logger.warning("Missing permission to delete channel %s (%s)", channel.name, channel.id)
        except discord.HTTPException:
            result.failures += 1
            logger.exception("Discord API error deleting channel %s (%s)", channel.name, channel.id)

    for category in categories:
        try:
            if not category.permissions_for(bot_member).manage_channels:
                continue
            await category.delete(reason="RAVN /clear-server confirmed by an authorized administrator")
            result.categories_deleted += 1
        except discord.Forbidden:
            result.failures += 1
            logger.warning("Missing permission to delete category %s (%s)", category.name, category.id)
        except discord.HTTPException:
            result.failures += 1
            logger.exception("Discord API error deleting category %s (%s)", category.name, category.id)

    return result


class ClearServerView(discord.ui.View):
    def __init__(self, requester_id: int) -> None:
        super().__init__(timeout=10)
        self.requester_id = requester_id
        self.message: discord.Message | None = None
        self.resolved = False

    def disable_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                "Only the server owner who started this confirmation can use these buttons.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if self.resolved:
            return
        self.resolved = True
        self.disable_buttons()
        if self.message:
            try:
                await self.message.edit(
                    content="Confirmation expired. No channels were deleted.",
                    view=self,
                )
            except discord.HTTPException:
                logger.info("Could not update the expired /clear-server confirmation message")

    @discord.ui.button(
        label="Confirm Delete",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="ravn:clear-server:confirm",
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.guild or not _is_server_owner(interaction):
            await interaction.response.send_message(
                "Only the server owner can confirm this action.",
                ephemeral=True,
            )
            return

        self.resolved = True
        self.disable_buttons()
        await interaction.response.defer(ephemeral=True)
        if self.message:
            try:
                await self.message.edit(content="Deleting manageable channels and categories…", view=self)
            except discord.HTTPException:
                logger.info("Could not update the active /clear-server confirmation message")

        result = await _delete_managed_channels(interaction.guild)
        status = (
            f"Deleted {result.channels_deleted} channel(s) and "
            f"{result.categories_deleted} categor(ies)."
        )
        if result.failures:
            status += f" {result.failures} object(s) could not be deleted because of permissions or Discord API errors."
        await interaction.followup.send(
            status,
            ephemeral=True,
        )

    @discord.ui.button(
        label="Cancel",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="ravn:clear-server:cancel",
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.resolved = True
        self.disable_buttons()
        await interaction.response.edit_message(
            content="Clear server cancelled. No channels or categories were deleted.",
            view=self,
        )


def register(bot: discord.Client) -> None:
    @bot.tree.command(
        name="clear-server",
        description="Delete all channels and categories the bot can manage after confirmation.",
    )
    @discord.app_commands.default_permissions(administrator=True)
    @discord.app_commands.check(_is_server_owner)
    async def clear_server(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used inside a server.",
                ephemeral=True,
            )
            return

        view = ClearServerView(interaction.user.id)
        embed = ravn_embed(
            "⚠️ DELETE SERVER CHANNELS",
            "This will permanently delete all categories and channels that the bot has permission to manage. "
            "This cannot be undone.",
            colour=DANGER,
            footer="RAVN Server Manager • Confirmation expires in 10 seconds",
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
