from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone

import discord

from .config import STAFF_ROLE_NAMES
from .embeds import ARK_BLUE, DANGER, SUCCESS, brand_embed, bot_avatar_url, ravn_embed, ticket_info_embed

logger = logging.getLogger(__name__)

TICKET_TYPES = {
    "support": ("🎫 Support", "General help with the RAVN community."),
    "player-report": ("🚨 Player Report", "Report a player, tribe, or incident."),
    "staff-report": ("🛡️ Staff Report", "Send a private report about a staff matter."),
    "donation": ("💰 Donation Support", "Questions about supporting the server."),
    "technical": ("🔧 Technical Support", "Technical help with Discord or the game server."),
}


def _is_staff(member: discord.Member) -> bool:
    return member.guild_permissions.manage_guild or any(
        role.name in STAFF_ROLE_NAMES for role in member.roles
    )


def _ticket_logs(guild: discord.Guild) -> discord.TextChannel | None:
    return discord.utils.find(
        lambda channel: channel.name == "🎫・ticket-logs",
        guild.text_channels,
    )


async def _transcript(channel: discord.TextChannel) -> discord.File:
    metadata = _ticket_metadata(channel)
    lines: list[str] = [
        f"RAVN ticket transcript: #{channel.name}",
        f"Ticket creator: {metadata.get('ticket_creator', 'Unknown')}",
        f"Ticket type: {metadata.get('type', 'Unknown')}",
        f"Ticket channel: {channel.name}",
        f"Claimed by: {metadata.get('claimed_by', 'Unclaimed')}",
        f"Created time: {metadata.get('created_at', 'Unknown')}",
        f"Closed time: {datetime.now(timezone.utc).isoformat()}",
        "-" * 72,
    ]
    messages = [message async for message in channel.history(limit=None, oldest_first=True)]
    for message in messages:
        timestamp = message.created_at.isoformat()
        attachments = " ".join(attachment.url for attachment in message.attachments)
        content = message.content or "[embed/component/attachment]"
        lines.append(f"[{timestamp}] {message.author} ({message.author.id}): {content} {attachments}".strip())
    payload = "\n".join(lines).encode("utf-8")
    return discord.File(io.BytesIO(payload), filename=f"{channel.name}-transcript.txt")


def _ticket_metadata(channel: discord.TextChannel) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in (channel.topic or "").split(";"):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        values[key] = value
    if owner_id := values.get("ticket_owner"):
        values["ticket_creator"] = f"<@{owner_id}>"
    if claimed_id := values.get("claimed_by"):
        values["claimed_by"] = "Unclaimed" if claimed_id == "unclaimed" else f"<@{claimed_id}>"
    return values


async def _find_ticket_category(guild: discord.Guild) -> discord.CategoryChannel:
    category = discord.utils.get(guild.categories, name="🎫 SUPPORT")
    if category:
        return category
    raise LookupError("The 🎫 SUPPORT category is missing. Run /setup-server first.")


async def create_ticket(
    interaction: discord.Interaction,
    ticket_type: str,
    details: dict[str, str],
) -> None:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Tickets can only be opened inside a server.", ephemeral=True)
        return

    try:
        category = await _find_ticket_category(interaction.guild)
    except LookupError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    marker = f"ticket_owner:{interaction.user.id};type:{ticket_type}"
    existing = discord.utils.find(
        lambda channel: isinstance(channel, discord.TextChannel)
        and channel.category_id == category.id
        and channel.topic
        and marker in channel.topic,
        interaction.guild.channels,
    )
    if existing and "state:closed" not in (existing.topic or ""):
        await interaction.response.send_message(
            f"You already have an open {TICKET_TYPES[ticket_type][0]} ticket: {existing.mention}",
            ephemeral=True,
        )
        return

    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True,
        ),
    }
    staff_roles = [role for role in interaction.guild.roles if role.name in STAFF_ROLE_NAMES]
    if not staff_roles:
        await interaction.response.send_message(
            "No staff roles were found. Ask an administrator to run `/setup-server` first.",
            ephemeral=True,
        )
        return
    for role in staff_roles:
        overwrites[role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
        )

    label, description = TICKET_TYPES[ticket_type]
    safe_name = re.sub(r"[^a-z0-9-]+", "-", interaction.user.display_name.lower()).strip("-")[:35]
    channel = await category.create_text_channel(
        f"ticket-{ticket_type}-{safe_name or interaction.user.id}",
        overwrites=overwrites,
        topic=(
            f"{marker};state:open;claimed_by:unclaimed;"
            f"created_at:{datetime.now(timezone.utc).isoformat()}"
        ),
        reason=f"RAVN {ticket_type} ticket",
    )
    embed = ravn_embed(
        f"{label} ticket",
        f"{description}\n\nA member of the support team will be with you shortly. Keep relevant evidence and details in this channel.",
        colour=ARK_BLUE,
    )
    embed.add_field(name="Opened by", value=interaction.user.mention, inline=True)
    embed.add_field(name="Name / tribe / player", value=details["name"], inline=True)
    embed.add_field(name="Map / server", value=details["map"], inline=True)
    embed.add_field(name="Reason / details", value=details["reason"], inline=False)
    embed.add_field(name="Next step", value="Use the controls below to claim or close this ticket.", inline=True)
    await channel.send(
        content=interaction.user.mention,
        embed=brand_embed(embed, bot_avatar_url(interaction.client)),
        view=TicketControlView(),
    )
    await interaction.response.send_message(f"Your private ticket is ready: {channel.mention}", ephemeral=True)


class TicketDetailsModal(discord.ui.Modal):
    def __init__(self, ticket_type: str) -> None:
        label, _description = TICKET_TYPES[ticket_type]
        super().__init__(title=f"{label} details"[:45])
        self.ticket_type = ticket_type
        self.name_input = discord.ui.TextInput(
            label="Name / tribe / player",
            placeholder="Who is this ticket about?",
            max_length=100,
            required=True,
        )
        self.map_input = discord.ui.TextInput(
            label="Map / server",
            placeholder="For example: The Island - EU 123",
            max_length=100,
            required=True,
        )
        self.reason_input = discord.ui.TextInput(
            label="Reason / details",
            placeholder="Explain what you need help with or what happened.",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True,
        )
        self.add_item(self.name_input)
        self.add_item(self.map_input)
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        details = {
            "name": self.name_input.value.strip(),
            "map": self.map_input.value.strip(),
            "reason": self.reason_input.value.strip(),
        }
        if not all(details.values()):
            await interaction.response.send_message(
                "Please complete your name, map/server, and reason before opening a ticket.",
                ephemeral=True,
            )
            return
        await create_ticket(interaction, self.ticket_type, details)


class TicketPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Support", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="ravn:ticket:support")
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketDetailsModal("support"))

    @discord.ui.button(label="Player Report", emoji="🚨", style=discord.ButtonStyle.danger, custom_id="ravn:ticket:player-report")
    async def player_report(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketDetailsModal("player-report"))

    @discord.ui.button(label="Staff Report", emoji="🛡️", style=discord.ButtonStyle.secondary, custom_id="ravn:ticket:staff-report")
    async def staff_report(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketDetailsModal("staff-report"))

    @discord.ui.button(label="Donation Support", emoji="💰", style=discord.ButtonStyle.success, custom_id="ravn:ticket:donation")
    async def donation(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketDetailsModal("donation"))

    @discord.ui.button(label="Technical Support", emoji="🔧", style=discord.ButtonStyle.secondary, custom_id="ravn:ticket:technical")
    async def technical(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(TicketDetailsModal("technical"))


class TicketControlView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.secondary, custom_id="ravn:ticket:close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not _is_staff(interaction.user):
            await interaction.response.send_message("Only staff can close a ticket.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        await interaction.response.defer()
        transcript = await _transcript(interaction.channel)
        logs = _ticket_logs(interaction.guild)
        if logs:
            await logs.send(
                embed=ravn_embed(
                    "🔒 Ticket closed",
                    f"{interaction.channel.mention} was closed by {interaction.user.mention}.",
                    colour=SUCCESS,
                ),
                file=transcript,
            )
        overwrites = interaction.channel.overwrites
        for target in list(overwrites):
            if isinstance(target, discord.Member):
                overwrites[target] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
        metadata = _ticket_metadata(interaction.channel)
        claimed_by = metadata.get("claimed_by", "unclaimed").replace("<@", "").replace(">", "")
        closed_topic = (
            f"ticket_owner:{metadata.get('ticket_owner', 'unknown')};"
            f"type:{metadata.get('type', 'unknown')};state:closed;"
            f"claimed_by:{claimed_by};created_at:{metadata.get('created_at', 'unknown')}"
        )
        await interaction.channel.edit(
            name=f"closed-{interaction.channel.name}"[:100],
            overwrites=overwrites,
            topic=closed_topic,
            reason=f"Ticket closed by {interaction.user}",
        )
        await interaction.followup.send("Ticket closed. A transcript was sent to the ticket logs.")

    @discord.ui.button(label="Claim Ticket", emoji="👤", style=discord.ButtonStyle.primary, custom_id="ravn:ticket:claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not _is_staff(interaction.user):
            await interaction.response.send_message("Only staff can claim a ticket.", ephemeral=True)
            return
        if isinstance(interaction.channel, discord.TextChannel):
            metadata = _ticket_metadata(interaction.channel)
            await interaction.channel.edit(
                topic=(
                    f"ticket_owner:{metadata.get('ticket_owner', 'unknown')};"
                    f"type:{metadata.get('type', 'unknown')};state:open;"
                    f"claimed_by:{interaction.user.id};"
                    f"created_at:{metadata.get('created_at', 'unknown')}"
                ),
                reason=f"Ticket claimed by {interaction.user}",
            )
            await interaction.channel.send(
                embed=ravn_embed(
                    "👤 Ticket claimed",
                    f"This ticket is now being handled by {interaction.user.mention}.",
                    colour=SUCCESS,
                )
            )
        await interaction.response.send_message("Ticket claimed.", ephemeral=True)

    @discord.ui.button(label="Delete Ticket", emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="ravn:ticket:delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not _is_staff(interaction.user) or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Only staff can delete a ticket.", ephemeral=True)
            return
        await interaction.response.defer()
        transcript = await _transcript(interaction.channel)
        logs = _ticket_logs(interaction.guild)
        if logs:
            await logs.send(
                embed=ravn_embed(
                    "🗑️ Ticket deleted",
                    f"#{interaction.channel.name} was deleted by {interaction.user.mention}.",
                    colour=DANGER,
                ),
                file=transcript,
            )
        await interaction.channel.delete(reason=f"Ticket deleted by {interaction.user}")


def register(bot: discord.Client) -> None:
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())

    @bot.tree.command(name="ticket", description="Post the RAVN private support ticket panel.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_panel(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            embed=brand_embed(ticket_info_embed(), bot_avatar_url(interaction.client)),
            view=TicketPanelView(),
        )
