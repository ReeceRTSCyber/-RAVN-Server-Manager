from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import discord

from .config import (
    CATEGORY_CHANNELS,
    INFO_CHANNELS,
    MANAGEMENT_ROLE_NAMES,
    PRIVATE_CATEGORIES,
    REMOVED_CATEGORIES,
    REMOVED_CHANNELS,
    ROLE_GROUPS,
    ROLE_NAMES,
    STAFF_ROLE_NAMES,
    TRIBE_ROLE_NAMES,
    VOICE_CATEGORIES,
)
from .embeds import (
    announcements_embed,
    brand_embed,
    recruitment_embed,
    reports_embed,
    rules_embed,
    server_info_embed,
    ticket_info_embed,
    trading_rules_embed,
    wipe_info_embed,
)
from .role_selection import (
    MiscRoleView,
    PingRoleView,
    misc_roles_embed,
    ping_roles_embed,
)
from .tickets import TicketPanelView

logger = logging.getLogger(__name__)

LOGO_ASSET_PATH = (
    Path(__file__).resolve().parents[1]
    / "attached_assets"
    / "IMG_0975_1789776307339.png"
)
LOGO_FILENAME = "ravn-logo.png"


@dataclass
class SetupResult:
    roles_created: int = 0
    categories_created: int = 0
    channels_created: int = 0
    messages_seeded: int = 0
    channels_removed: int = 0
    categories_removed: int = 0
    cleanup_failures: int = 0


def _role(guild: discord.Guild, name: str) -> discord.Role | None:
    return discord.utils.get(guild.roles, name=name)


async def ensure_roles(guild: discord.Guild, result: SetupResult) -> dict[str, discord.Role]:
    roles: dict[str, discord.Role] = {}
    role_permissions: dict[str, discord.Permissions] = {
        "👑 Owner": discord.Permissions.all(),
        "🛡️ Co-Owner": discord.Permissions(
            administrator=True,
            manage_guild=True,
            manage_channels=True,
            manage_roles=True,
            manage_messages=True,
            kick_members=True,
            ban_members=True,
            moderate_members=True,
            view_audit_log=True,
        ),
        "⚡ Server Manager": discord.Permissions(
            manage_guild=True,
            manage_channels=True,
            manage_roles=True,
            manage_messages=True,
            view_audit_log=True,
        ),
        "🔧 Head Admin": discord.Permissions(
            manage_channels=True,
            manage_roles=True,
            manage_messages=True,
            kick_members=True,
            ban_members=True,
            moderate_members=True,
            view_audit_log=True,
        ),
        "🛡️ Admin": discord.Permissions(
            manage_messages=True,
            kick_members=True,
            ban_members=True,
            moderate_members=True,
            view_audit_log=True,
        ),
        "🔨 Moderator": discord.Permissions(
            manage_messages=True,
            kick_members=True,
            moderate_members=True,
            view_audit_log=True,
        ),
        "🧹 Trial Moderator": discord.Permissions(
            manage_messages=True,
            moderate_members=True,
        ),
        "🤖 Bot": discord.Permissions(
            manage_messages=True,
            manage_channels=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
        ),
    }

    for group in ROLE_GROUPS.values():
        for name in group:
            existing = _role(guild, name)
            if existing:
                roles[name] = existing
                continue
            created = await guild.create_role(
                name=name,
                permissions=role_permissions.get(name, discord.Permissions.none()),
                mentionable=name in {
                    "📣 Small Announcements",
                    "🎉 Giveaway Ping",
                    "🔄 Rollback Ping",
                    "♻️ Restart Ping",
                    "🦖 Event Dino Ping",
                    "🔻 Event Crate Ping",
                    "🪨 Golem Ping",
                    "🚀 Events Ping",
                },
                reason="RAVN Server Manager setup",
            )
            roles[name] = created
            result.roles_created += 1

    # Discord creates new roles near the bottom. Set the requested hierarchy
    # explicitly while preserving the managed integration roles.
    ordered = [name for group in ROLE_GROUPS.values() for name in group]
    try:
        positions = {roles[name]: index + 1 for index, name in enumerate(reversed(ordered))}
        await guild.edit_role_positions(positions=positions, reason="RAVN Server Manager role hierarchy")
    except discord.HTTPException:
        logger.warning("Could not reorder roles in guild %s", guild.id)
    return roles


def _overwrites(
    guild: discord.Guild,
    roles: dict[str, discord.Role],
    *,
    private: bool = False,
    info: bool = False,
    tribe: bool = False,
) -> dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
    everyone = guild.default_role
    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {}

    if private:
        overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
        for name in STAFF_ROLE_NAMES:
            if name in roles:
                overwrites[roles[name]] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )
        for name in MANAGEMENT_ROLE_NAMES:
            if name in roles:
                overwrites[roles[name]] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                )
        return overwrites

    if info:
        overwrites[everyone] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            add_reactions=False,
        )
    else:
        overwrites[everyone] = discord.PermissionOverwrite(view_channel=not tribe, send_messages=not tribe)

    if "⭐ Member" in roles:
        overwrites[roles["⭐ Member"]] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    if "🆕 New Member" in roles and not tribe:
        overwrites[roles["🆕 New Member"]] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    if tribe:
        for name in TRIBE_ROLE_NAMES:
            if name in roles:
                overwrites[roles[name]] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    return overwrites


async def _get_or_create_category(
    guild: discord.Guild,
    name: str,
    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite],
    result: SetupResult,
) -> discord.CategoryChannel:
    category = discord.utils.find(lambda item: item.name == name, guild.categories)
    if category:
        try:
            await category.edit(overwrites=overwrites, reason="RAVN Server Manager permissions")
        except discord.HTTPException:
            logger.warning("Could not update permissions for category %s", name)
        return category
    result.categories_created += 1
    return await guild.create_category(name, overwrites=overwrites, reason="RAVN Server Manager setup")


async def _get_or_create_text_channel(
    category: discord.CategoryChannel,
    name: str,
    result: SetupResult,
) -> discord.TextChannel:
    channel = discord.utils.find(lambda item: item.name == name, category.text_channels)
    if channel:
        return channel
    result.channels_created += 1
    return await category.create_text_channel(name, reason="RAVN Server Manager setup")


async def _get_or_create_voice_channel(
    category: discord.CategoryChannel,
    name: str,
    result: SetupResult,
) -> discord.VoiceChannel:
    channel = discord.utils.find(lambda item: item.name == name, category.voice_channels)
    if channel:
        return channel
    result.channels_created += 1
    return await category.create_voice_channel(name, reason="RAVN Server Manager setup")


async def _remove_legacy_content(guild: discord.Guild, result: SetupResult) -> None:
    """Remove only channels/categories explicitly retired from the layout."""
    bot_member = guild.me
    if not bot_member:
        result.cleanup_failures += 1
        logger.error("Cannot clean retired content in guild %s: bot member unavailable", guild.id)
        return

    for category_name in REMOVED_CATEGORIES:
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            continue
        for channel in list(category.channels):
            try:
                if not channel.permissions_for(bot_member).manage_channels:
                    result.cleanup_failures += 1
                    continue
                await channel.delete(reason="RAVN Server Manager retired channel cleanup")
                result.channels_removed += 1
            except discord.Forbidden:
                result.cleanup_failures += 1
                logger.warning("Missing permission to remove retired channel %s", channel.name)
            except discord.HTTPException:
                result.cleanup_failures += 1
                logger.exception("Discord API error removing retired channel %s", channel.name)
        try:
            if category.permissions_for(bot_member).manage_channels:
                await category.delete(reason="RAVN Server Manager retired category cleanup")
                result.categories_removed += 1
            else:
                result.cleanup_failures += 1
        except discord.Forbidden:
            result.cleanup_failures += 1
            logger.warning("Missing permission to remove retired category %s", category.name)
        except discord.HTTPException:
            result.cleanup_failures += 1
            logger.exception("Discord API error removing retired category %s", category.name)

    for category_name, channel_names in REMOVED_CHANNELS.items():
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            continue
        for channel_name in channel_names:
            channel = discord.utils.find(lambda item: item.name == channel_name, category.channels)
            if not channel:
                continue
            try:
                if not channel.permissions_for(bot_member).manage_channels:
                    result.cleanup_failures += 1
                    continue
                await channel.delete(reason="RAVN Server Manager retired channel cleanup")
                result.channels_removed += 1
            except discord.Forbidden:
                result.cleanup_failures += 1
                logger.warning("Missing permission to remove retired channel %s", channel.name)
            except discord.HTTPException:
                result.cleanup_failures += 1
                logger.exception("Discord API error removing retired channel %s", channel.name)


async def _seed_embed(
    channel: discord.TextChannel,
    embed: discord.Embed,
    view: discord.ui.View | None = None,
    *,
    titles: set[str] | None = None,
    image_url: str | None = None,
    image_path: Path | None = None,
) -> bool:
    marker = "RAVN Server Manager"
    embed = brand_embed(embed, image_url)

    def _logo_file() -> discord.File | None:
        if not image_path or not image_path.is_file():
            return None
        return discord.File(str(image_path), filename=LOGO_FILENAME)

    try:
        async for message in channel.history(limit=30):
            if (
                message.author == channel.guild.me
                and message.embeds
                and message.embeds[0].footer.text
                and marker in message.embeds[0].footer.text
                and (titles is None or message.embeds[0].title in titles)
            ):
                edit_kwargs: dict[str, object] = {"embed": embed, "view": view}
                if image_path:
                    logo_file = _logo_file()
                    if logo_file:
                        edit_kwargs["attachments"] = [logo_file]
                await message.edit(**edit_kwargs)
                return True
        logo_file = _logo_file()
        if logo_file:
            await channel.send(embed=embed, view=view, file=logo_file)
        else:
            await channel.send(embed=embed, view=view)
        return True
    except (discord.Forbidden, discord.HTTPException):
        logger.warning("Could not seed channel %s", channel.name)
        return False


async def ensure_ping_roles(guild: discord.Guild, result: SetupResult) -> dict[str, discord.Role]:
    """Create only the self-assignable ping roles used by the role panel.

    This intentionally does not create/reorder any other roles and does not
    create, edit, or delete categories/channels.
    """
    from .config import PING_ROLE_NAMES

    roles: dict[str, discord.Role] = {}
    mentionable = set(PING_ROLE_NAMES)

    for name in PING_ROLE_NAMES:
        existing = _role(guild, name)
        if existing:
            roles[name] = existing
            continue

        created = await guild.create_role(
            name=name,
            permissions=discord.Permissions.none(),
            mentionable=name in mentionable,
            reason="RAVN Server Manager ping roles",
        )
        roles[name] = created
        result.roles_created += 1

    return roles


async def provision_guild(guild: discord.Guild) -> SetupResult:
    """Set up only the RAVN ping roles and refresh the existing ping panel.

    /setup-server deliberately no longer provisions the Discord layout. The
    server's categories/channels and all non-ping roles are left untouched.
    """
    result = SetupResult()
    await ensure_ping_roles(guild, result)

    role_channel = discord.utils.find(
        lambda item: item.name == "🎭・role-selection",
        guild.text_channels,
    )
    if role_channel:
        bot_image_url = str(guild.me.display_avatar.url) if guild.me else None
        setup_image_url = "attachment://ravn-logo.png" if LOGO_ASSET_PATH.is_file() else bot_image_url
        setup_image_path = LOGO_ASSET_PATH if LOGO_ASSET_PATH.is_file() else None

        if await _seed_embed(
            role_channel,
            ping_roles_embed(),
            PingRoleView(),
            titles={"PING ROLES", "🎭 Choose Your Roles"},
            image_url=setup_image_url,
            image_path=setup_image_path,
        ):
            result.messages_seeded += 1

    return result


def setup_command(bot: discord.Client) -> None:
    @bot.tree.command(name="setup-server", description="Create or repair the complete RAVN Discord server structure.")
    @discord.app_commands.default_permissions(administrator=True)
    @discord.app_commands.check(lambda interaction: bool(interaction.guild and interaction.guild.owner_id == interaction.user.id))
    async def setup_server(interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("This command can only run inside a server.", ephemeral=True)
            return
        try:
            result = await provision_guild(interaction.guild)
            cleanup_note = (
                f"{result.cleanup_failures} retired objects could not be removed. "
                if result.cleanup_failures
                else ""
            )
            summary = (
                "Server setup complete. "
                f"Created {result.roles_created} roles, {result.categories_created} categories, "
                f"{result.channels_created} channels, removed {result.channels_removed} retired channels and "
                f"{result.categories_removed} retired categories, and seeded {result.messages_seeded} embeds. "
                f"{cleanup_note}Existing objects were preserved."
            )
            await interaction.followup.send(
                summary,
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Discord denied the setup. Give the bot Manage Server, Manage Channels, Manage Roles, "
                "and permission to manage roles above the roles it must assign.",
                ephemeral=True,
            )
        except discord.HTTPException as exc:
            logger.exception("Guild setup failed")
            await interaction.followup.send(f"Discord returned an error while setting up the server: {exc}", ephemeral=True)
