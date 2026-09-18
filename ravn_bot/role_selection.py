from __future__ import annotations

import logging

import discord

from .config import NOTIFICATION_ROLE_NAMES, PLATFORM_ROLE_NAMES
from .embeds import ARK_BLUE, ravn_embed

logger = logging.getLogger(__name__)


def _role_map(guild: discord.Guild, names: list[str]) -> dict[str, discord.Role]:
    return {
        name: role
        for name in names
        if (role := discord.utils.get(guild.roles, name=name)) is not None
    }


async def _apply_selection(
    interaction: discord.Interaction,
    selected_names: list[str],
    allowed_names: list[str],
) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "This role menu can only be used inside a server.",
            ephemeral=True,
        )
        return

    roles = _role_map(interaction.guild, allowed_names)
    missing = [name for name in allowed_names if name not in roles]
    if missing:
        logger.error("Role selection is missing roles in guild %s: %s", interaction.guild.id, missing)
        await interaction.response.send_message(
            "Role selection is unavailable because the server roles are incomplete. "
            "Ask an administrator to run `/setup-server` again.",
            ephemeral=True,
        )
        return

    if interaction.guild.me and any(
        role.position >= interaction.guild.me.top_role.position for role in roles.values()
    ):
        await interaction.response.send_message(
            "I cannot manage these roles because my bot role is below them in the hierarchy. "
            "Move the bot role above the selectable roles, then try again.",
            ephemeral=True,
        )
        return

    selected = set(selected_names)
    current = {role for role in interaction.user.roles if role in roles.values()}
    to_remove = [role for role in current if role.name not in selected]
    to_add = [role for name, role in roles.items() if name in selected and role not in current]
    try:
        if to_remove:
            await interaction.user.remove_roles(*to_remove, reason="RAVN self-assigned role selection")
        if to_add:
            await interaction.user.add_roles(*to_add, reason="RAVN self-assigned role selection")
    except discord.Forbidden:
        await interaction.response.send_message(
            "Discord denied the role update. Check that the bot role is above the selectable roles "
            "and has Manage Roles.",
            ephemeral=True,
        )
        return
    except discord.HTTPException:
        logger.exception("Discord API error while updating self-assigned roles")
        await interaction.response.send_message(
            "Discord could not update your roles right now. Please try again.",
            ephemeral=True,
        )
        return

    selected_text = ", ".join(selected_names) if selected_names else "none"
    await interaction.response.send_message(
        f"Your selection is updated: {selected_text}.",
        ephemeral=True,
    )


class RoleSelectionView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

        platform = discord.ui.Select(
            custom_id="ravn:roles:platform",
            placeholder="Choose Your Roles — platform",
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(label="PC", value="🎮 PC", emoji="🎮"),
                discord.SelectOption(label="Xbox", value="🎮 Xbox", emoji="🎮"),
                discord.SelectOption(label="PlayStation", value="🎮 PlayStation", emoji="🎮"),
            ],
        )
        platform.callback = self.platform_callback
        self.add_item(platform)

        notifications = discord.ui.Select(
            custom_id="ravn:roles:notifications",
            placeholder="Choose Your Roles — notifications",
            min_values=0,
            max_values=6,
            options=[
                discord.SelectOption(label="Announcements", value="📢 Announcements", emoji="📢"),
                discord.SelectOption(label="PvP", value="⚔️ PvP", emoji="⚔️"),
                discord.SelectOption(label="Raids", value="💀 Raids", emoji="💀"),
                discord.SelectOption(label="Bosses", value="🦖 Bosses", emoji="🦖"),
                discord.SelectOption(label="Trading", value="💰 Trading", emoji="💰"),
                discord.SelectOption(label="Events", value="🎉 Events", emoji="🎉"),
            ],
        )
        notifications.callback = self.notifications_callback
        self.add_item(notifications)

    async def platform_callback(self, interaction: discord.Interaction) -> None:
        select = interaction.data.get("values", []) if interaction.data else []
        await _apply_selection(interaction, list(select), PLATFORM_ROLE_NAMES)

    async def notifications_callback(self, interaction: discord.Interaction) -> None:
        select = interaction.data.get("values", []) if interaction.data else []
        await _apply_selection(interaction, list(select), NOTIFICATION_ROLE_NAMES)


def role_selection_embed() -> discord.Embed:
    embed = ravn_embed(
        "🎭 Choose Your Roles",
        "Select one platform and any notification roles you want. Changing a selection automatically "
        "adds and removes only the self-assignable roles below.",
        colour=ARK_BLUE,
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


def register(bot: discord.Client) -> None:
    """Register the role menu as a persistent view."""
    bot.add_view(RoleSelectionView())