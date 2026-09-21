from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from .clear_server import register as register_clear_server
from .config import load_settings
from .embeds import brand_embed, bot_avatar_url, welcome_embed
from .features import register as register_features
from .moderation import register as register_moderation
from .role_selection import register as register_role_selection
from .setup_server import setup_command
from .tickets import register as register_tickets

logger = logging.getLogger(__name__)


class RavnBot(commands.Bot):
    def __init__(self, settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            description="RAVN Server Manager for ARK Survival Ascended PvP communities.",
        )
        self.settings = settings

    async def setup_hook(self) -> None:
        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info(
                "Synced %s commands to configured guild %s",
                len(synced),
                self.settings.guild_id,
            )
        else:
            synced = await self.tree.sync()
            logger.info("Synced %s global commands", len(synced))

    async def on_ready(self) -> None:
        logger.info(
            "RAVN Server Manager online as %s in %s guild(s)",
            self.user,
            len(self.guilds),
        )

    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id") if interaction.data else None
            logger.info(
                "INTERACTION RECEIVED | component | custom_id=%s | user=%s | guild=%s",
                custom_id,
                interaction.user,
                interaction.guild_id,
            )
        elif interaction.type == discord.InteractionType.modal_submit:
            custom_id = interaction.data.get("custom_id") if interaction.data else None
            logger.info(
                "INTERACTION RECEIVED | modal | custom_id=%s | user=%s | guild=%s",
                custom_id,
                interaction.user,
                interaction.guild_id,
            )

    async def on_member_join(self, member: discord.Member) -> None:
        channel = discord.utils.get(member.guild.text_channels, name="👋・welcome")
        if channel:
            await channel.send(embed=brand_embed(welcome_embed(member), bot_avatar_url(self)))

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "You do not have permission to use this command."
        elif isinstance(error, app_commands.CommandOnCooldown):
            message = "That command is temporarily rate-limited. Try again shortly."
        else:
            logger.exception("Application command failed", exc_info=error)
            message = "Something went wrong while running that command."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


def create_bot() -> tuple[RavnBot, str]:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = RavnBot(settings)
    setup_command(bot)
    register_tickets(bot)
    register_role_selection(bot)
    register_moderation(bot)
    register_features(bot)
    register_clear_server(bot)
    return bot, settings.token


def run() -> None:
    bot, token = create_bot()
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    run()
