from __future__ import annotations

import logging

import discord

from .config import PING_ROLE_NAMES, PLATFORM_ROLE_NAMES, REGION_ROLE_NAMES
from .embeds import ARK_BLUE, brand_embed, ravn_embed

logger = logging.getLogger(__name__)


# Custom Discord emoji IDs supplied for the reaction-role buttons.
REACTION_ROLE_EMOJIS = {
    "PS5": discord.PartialEmoji(name="PS5", id=1551557280581816461),
    "Xbox": discord.PartialEmoji(name="Xbox", id=1551557335422603306),
    "PC": discord.PartialEmoji(name="PC", id=1551557384881705004),
    "Golem Ping": discord.PartialEmoji(name="golem", id=1551461825806209086),
    "Event Crate Ping": discord.PartialEmoji(name="event_crate", id=1551557177892671529),
    "Event Dino Ping": discord.PartialEmoji(name="event_dino", id=1551557466188152964),
    "Rollback Ping": discord.PartialEmoji(name="rollback", id=1551462057965264937),
}

# Actual Discord role IDs paired with the custom reaction-role emojis.
REACTION_ROLE_IDS = {
    "PS5": 1550662095337558076,
    "Xbox": 1550662098697330819,
    "PC": 1550662096549711936,
    "Golem Ping": 1550662112655712388,
    "Event Crate Ping": 1550662111049416806,
    "Event Dino Ping": 1550662110269145109,
    "Rollback Ping": 1550662107954024579,
}


async def _toggle_role(
    interaction: discord.Interaction,
    role_name: str,
    *,
    role_id: int | None = None,
    exclusive_names: list[str] | None = None,
    exclusive_ids: list[int] | None = None,
) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "This role panel can only be used inside a server.",
            ephemeral=True,
        )
        return

    role = (
        interaction.guild.get_role(role_id)
        if role_id is not None
        else discord.utils.get(interaction.guild.roles, name=role_name)
    )

    if not role:
        logger.error(
            "Role selection is missing role %s in guild %s",
            role_name,
            interaction.guild.id,
        )
        await interaction.response.send_message(
            "This role is not available yet. Ask an administrator to run "
            "`/setup-server` again.",
            ephemeral=True,
        )
        return

    if interaction.guild.me and role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message(
            "I cannot manage this role because the bot role is below it. "
            "Move the bot role above the self-assignable roles, then try again.",
            ephemeral=True,
        )
        return

    try:
        if role in interaction.user.roles:
            await interaction.user.remove_roles(
                role,
                reason="RAVN reaction role removed",
            )
            message = f"Removed {role.mention}."
        else:
            roles_to_remove: list[discord.Role] = []

            if exclusive_ids:
                roles_to_remove.extend(
                    other
                    for other_id in exclusive_ids
                    if (other := interaction.guild.get_role(other_id))
                    and other in interaction.user.roles
                    and other != role
                )

            if exclusive_names:
                roles_to_remove.extend(
                    other
                    for name in exclusive_names
                    if (other := discord.utils.get(
                        interaction.guild.roles,
                        name=name,
                    ))
                    and other in interaction.user.roles
                    and other != role
                )

            if roles_to_remove:
                await interaction.user.remove_roles(
                    *roles_to_remove,
                    reason="RAVN platform role changed",
                )

            await interaction.user.add_roles(
                role,
                reason="RAVN reaction role added",
            )
            message = f"Added {role.mention}."

    except discord.Forbidden:
        await interaction.response.send_message(
            "Discord denied the role update. Check that the bot has Manage Roles "
            "and its role is above the self-assignable roles.",
            ephemeral=True,
        )
        return

    except discord.HTTPException:
        logger.exception(
            "Discord API error while changing reaction role %s",
            role_name,
        )
        await interaction.response.send_message(
            "Discord could not update your role right now. Please try again.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        message,
        ephemeral=True,
    )


def _button_callback(
    role_name: str,
    *,
    role_id: int | None = None,
    exclusive_names: list[str] | None = None,
    exclusive_ids: list[int] | None = None,
):
    async def callback(interaction: discord.Interaction) -> None:
        await _toggle_role(
            interaction,
            role_name,
            role_id=role_id,
            exclusive_names=exclusive_names,
            exclusive_ids=exclusive_ids,
        )

    return callback


class PingRoleView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

        roles = [
            (
                "Small Announcements",
                PING_ROLE_NAMES[0],
                "📣",
                None,
            ),
            (
                "Giveaway Ping",
                PING_ROLE_NAMES[1],
                "🎉",
                None,
            ),
            (
                "Rollback Ping",
                PING_ROLE_NAMES[2],
                REACTION_ROLE_EMOJIS["Rollback Ping"],
                REACTION_ROLE_IDS["Rollback Ping"],
            ),
            (
                "Restart Ping",
                PING_ROLE_NAMES[3],
                "♻️",
                None,
            ),
            (
                "Event Dino Ping",
                PING_ROLE_NAMES[4],
                REACTION_ROLE_EMOJIS["Event Dino Ping"],
                REACTION_ROLE_IDS["Event Dino Ping"],
            ),
            (
                "Event Crate Ping",
                PING_ROLE_NAMES[5],
                REACTION_ROLE_EMOJIS["Event Crate Ping"],
                REACTION_ROLE_IDS["Event Crate Ping"],
            ),
            (
                "Golem Ping",
                PING_ROLE_NAMES[6],
                REACTION_ROLE_EMOJIS["Golem Ping"],
                REACTION_ROLE_IDS["Golem Ping"],
            ),
            (
                "Events Ping",
                PING_ROLE_NAMES[7],
                "🚀",
                None,
            ),
            (
                "Discord Event Ping",
                PING_ROLE_NAMES[8],
                "🎉",
                None,
            ),
        ]

        rows = [0, 1, 1, 2, 2, 3, 3, 4, 4]

        for index, (label, role_name, emoji, role_id) in enumerate(roles):
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"ravn:roles:ping:{role_name.split(' ', 1)[1].lower()}",
                row=rows[index],
            )

            button.callback = _button_callback(
                role_name,
                role_id=role_id,
            )

            self.add_item(button)


class MiscRoleView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

        roles = [
            (
                "PS5",
                PLATFORM_ROLE_NAMES[0],
                REACTION_ROLE_EMOJIS["PS5"],
                REACTION_ROLE_IDS["PS5"],
            ),
            (
                "PC",
                PLATFORM_ROLE_NAMES[1],
                REACTION_ROLE_EMOJIS["PC"],
                REACTION_ROLE_IDS["PC"],
            ),
            (
                "Xbox",
                PLATFORM_ROLE_NAMES[2],
                REACTION_ROLE_EMOJIS["Xbox"],
                REACTION_ROLE_IDS["Xbox"],
            ),
            (
                "Europe",
                REGION_ROLE_NAMES[0],
                "🇩🇪",
                None,
            ),
            (
                "NA",
                REGION_ROLE_NAMES[1],
                "🌎",
                None,
            ),
            (
                "UK",
                REGION_ROLE_NAMES[2],
                "🇬🇧",
                None,
            ),
            (
                "AUS",
                REGION_ROLE_NAMES[3],
                "🇦🇺",
                None,
            ),
        ]

        exclusive_platform_ids = [
            REACTION_ROLE_IDS["PS5"],
            REACTION_ROLE_IDS["PC"],
            REACTION_ROLE_IDS["Xbox"],
        ]

        exclusive_regions = REGION_ROLE_NAMES

        for index, (label, role_name, emoji, role_id) in enumerate(roles):
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"ravn:roles:platform:{label.lower()}",
                row=index // 3,
            )

            button.callback = _button_callback(
                role_name,
                role_id=role_id,
                exclusive_ids=(
                    exclusive_platform_ids
                    if role_id is not None
                    else None
                ),
                exclusive_names=(
                    exclusive_regions
                    if role_name in exclusive_regions
                    else None
                ),
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
        value=(
            "📣 Small Announcements  •  🎉 Giveaway Ping\n"
            "🔄 Rollback Ping  •  ♻️ Restart Ping\n"
            "🦖 Event Dino Ping  •  🔻 Event Crate Ping\n"
            "🪨 Golem Ping  •  🚀 Events Ping\n"
            "🎉 Discord Event Ping"
        ),
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
        name="Platform and region",
        value=(
            "🎮 PS5  •  🖥️ PC  •  🟢 Xbox\n"
            "🇩🇪 Europe  •  🌎 NA  •  🇬🇧 UK  •  🇦🇺 AUS"
        ),
        inline=False,
    )

    return brand_embed(embed, image_url)


def register(bot: discord.Client) -> None:
    """Register button-based reaction roles as persistent views."""
    bot.add_view(PingRoleView())
    bot.add_view(MiscRoleView())