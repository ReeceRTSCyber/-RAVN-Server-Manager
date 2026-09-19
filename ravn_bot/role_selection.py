from __future__ import annotations

import logging

import discord

from .config import PLATFORM_ROLE_NAMES
from .embeds import ARK_BLUE, brand_embed, ravn_embed

logger = logging.getLogger(__name__)


async def _toggle_role(
    interaction: discord.Interaction,
    role_name: str,
    *,
    exclusive_names: list[str] | None = None,
) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "This role panel can only be used inside a server.",
            ephemeral=True,
        )
        return

    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if not role:
        logger.error("Role selection is missing role %s in guild %s", role_name, interaction.guild.id)
        await interaction.response.send_message(
            "This role is not available yet. Ask an administrator to run `/setup-server` again.",
            ephemeral=True,
        )
        return

    if interaction.guild.me and role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message(
            "I cannot manage this role because the bot role is below it. Move the bot role above "
            "the self-assignable roles, then try again.",
            ephemeral=True,
        )
        return

    try:
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role, reason="RAVN reaction role removed")
            message = f"Removed {role.mention}."
        else:
            if exclusive_names:
                roles_to_remove = [
                    other
                    for name in exclusive_names
                    if (other := discord.utils.get(interaction.guild.roles, name=name))
                    and other in interaction.user.roles
                    and other != role
                ]
                if roles_to_remove:
                    await interaction.user.remove_roles(
                        *roles_to_remove,
                        reason="RAVN platform role changed",
                    )
            await interaction.user.add_roles(role, reason="RAVN reaction role added")
            message = f"Added {role.mention}."
    except discord.Forbidden:
        await interaction.response.send_message(
            "Discord denied the role update. Check that the bot has Manage Roles and its role "
            "is above the self-assignable roles.",
            ephemeral=True,
        )
        return
    except discord.HTTPException:
        logger.exception("Discord API error while changing reaction role %s", role_name)
        await interaction.response.send_message(
            "Discord could not update your role right now. Please try again.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(message, ephemeral=True)


def _button_callback(
    role_name: str,
    *,
    exclusive_names: list[str] | None = None,
):
    async def callback(interaction: discord.Interaction) -> None:
        await _toggle_role(interaction, role_name, exclusive_names=exclusive_names)

    return callback


class PingRoleView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        roles = [
            ("Announcements", "📢 Announcements", "📢"),
            ("PvP", "⚔️ PvP", "⚔️"),
            ("Raids", "💀 Raids", "💀"),
            ("Bosses", "🦖 Bosses", "🦖"),
            ("Trading", "💰 Trading", "💰"),
            ("Events", "🎉 Events", "🎉"),
        ]
        rows = [0, 1, 1, 2, 2, 3]
        for index, (label, role_name, emoji) in enumerate(roles):
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"ravn:roles:ping:{role_name.split(' ', 1)[1].lower()}",
                row=rows[index],
            )
            button.callback = _button_callback(role_name)
            self.add_item(button)


class MiscRoleView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        roles = [
            ("PC", "🎮 PC", "🎮"),
            ("Xbox", "🎮 Xbox", "🎮"),
            ("PlayStation", "🎮 PlayStation", "🎮"),
        ]
        for index, (label, role_name, emoji) in enumerate(roles):
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"ravn:roles:platform:{label.lower()}",
                row=index // 3,
            )
            button.callback = _button_callback(
                role_name,
                exclusive_names=PLATFORM_ROLE_NAMES,
            )
            self.add_item(button)


def ping_roles_embed(image_url: str | None = None) -> discord.Embed:
    embed = ravn_embed(
        "PING ROLES",
        "Click the buttons to receive ping roles!",
        colour=ARK_BLUE,
        footer="RAVN Server Manager • Reaction Roles",
    )
    embed.set_author(name="RAVN Server Manager")
    embed.add_field(
        name="Available pings",
        value="📢 Announcements  •  ⚔️ PvP  •  💀 Raids\n🦖 Bosses  •  💰 Trading  •  🎉 Events",
        inline=False,
    )
    return brand_embed(embed, image_url)


def misc_roles_embed(image_url: str | None = None) -> discord.Embed:
    embed = ravn_embed(
        "MISC ROLES",
        "Click the buttons to receive misc roles!",
        colour=ARK_BLUE,
        footer="RAVN Server Manager • Reaction Roles",
    )
    embed.set_author(name="RAVN Server Manager")
    embed.add_field(
        name="Platform",
        value="🎮 PC  •  🎮 Xbox  •  🎮 PlayStation",
        inline=False,
    )
    return brand_embed(embed, image_url)


def register(bot: discord.Client) -> None:
    """Register button-based reaction roles as persistent views."""
    bot.add_view(PingRoleView())
    bot.add_view(MiscRoleView())