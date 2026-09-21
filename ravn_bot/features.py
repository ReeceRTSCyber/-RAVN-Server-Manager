from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

EVENT_INTERVAL_SECONDS = 4 * 60 * 60
DINO_EVENT_ANSWERS = [
    "Rex", "Spino", "Therizinosaur", "Giganotosaurus", "Carcharodontosaurus",
    "Wyvern", "Rock Drake", "Managarmr", "Yutyrannus", "Direwolf",
    "Argentavis", "Quetzal", "Mammoth", "Doedicurus", "Ankylosaurus",
    "Stegosaurus", "Triceratops", "Baryonyx", "Mosasaurus", "Plesiosaur",
]
EVENT_SCHEDULER_STARTED = False
DINO_GIFT_CARD_VALUES = ["$1", "$2", "$3", "$4", "$5"]
VAULT_GIFT_CARD_VALUES = ["$5", "$6", "$7", "$8", "$9", "$10", "$11", "$12", "$13", "$14", "$15"]

import discord

from .embeds import (
    ARK_BLUE,
    RAVN_PURPLE,
    SUCCESS,
    announcements_embed,
    brand_embed,
    bot_avatar_url,
    event_embed,
    patch_notes_embed,
    recruitment_embed,
    ravn_embed,
)
from .tickets import _is_staff
from .case_system import create_case

logger = logging.getLogger(__name__)


PUNISHMENT_ROLE_NAMES = {
    "🔧 Head Admin",
    "🛡️ Admin",
    "⚡ Server Manager",
    "🛡️ Co-Owner",
    "👑 Owner",
}


def _can_issue_punishment(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    return any(role.name in PUNISHMENT_ROLE_NAMES for role in interaction.user.roles)


def _find_channel(guild: discord.Guild, name: str) -> discord.TextChannel | None:
    return discord.utils.get(guild.text_channels, name=name)


def _gift_code_for(event_type: str) -> str | None:
    # Codes are supplied securely through Railway environment variables.
    # Use comma-separated codes in RAVN_DINO_GIFT_CODES / RAVN_VAULT_GIFT_CODES.
    import os
    variable = "RAVN_DINO_GIFT_CODES" if event_type == "dino" else "RAVN_VAULT_GIFT_CODES"
    codes = [code.strip() for code in os.getenv(variable, "").split(",") if code.strip()]
    return random.choice(codes) if codes else None


def _scramble_dino(name: str) -> str:
    letters = list(name)
    if len(letters) < 2:
        return name
    original = "".join(letters)
    for _ in range(10):
        random.shuffle(letters)
        scrambled = "".join(letters)
        if scrambled.casefold() != original.casefold():
            return scrambled
    return scrambled


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
        await channel.send(embed=brand_embed(embed, bot_avatar_url(interaction.client)))
        await interaction.response.send_message(f"Your recruitment post is live in {channel.mention}.", ephemeral=True)


class GiveawayView(discord.ui.View):
    def __init__(self, prize: str, winners: int, ends_at: float) -> None:
        super().__init__(timeout=None)
        self.prize = prize
        self.winners = winners
        self.ends_at = ends_at
        self.entries: set[int] = set()
        self.message: discord.Message | None = None

    @discord.ui.button(label="Enter giveaway", emoji="🎉", style=discord.ButtonStyle.primary, custom_id="ravn:giveaway:enter")
    async def enter(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id in self.entries:
            await interaction.response.send_message("You are already entered in this giveaway.", ephemeral=True)
            return
        self.entries.add(interaction.user.id)
        await interaction.response.send_message("🎉 You are entered. Good luck!", ephemeral=True)

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
                embed=ravn_embed("🎉 RAVN GIVEAWAY ENDED", description, colour=RAVN_PURPLE, footer="RAVN Server Manager • Giveaways"),
                view=None,
            )
        except discord.HTTPException:
            logger.warning("Could not finish giveaway message %s", self.message.id)

class DinoGuessModal(discord.ui.Modal, title="Guess the Dino"):
    guess = discord.ui.TextInput(label="Your dinosaur guess", placeholder="e.g. Rex", max_length=80)

    def __init__(self, game: "DinoGuessView") -> None:
        super().__init__()
        self.game = game

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.game.winner_id is not None:
            await interaction.response.send_message("🏆 This event has already been won.", ephemeral=True)
            return
        if self.guess.value.strip().casefold() != self.game.answer.casefold():
            await interaction.response.send_message("❌ Wrong dinosaur! Try again.", ephemeral=True)
            return
        self.game.winner_id = interaction.user.id
        self.game.stop()
        gift_message = ""
        if self.game.gift_card_code:
            try:
                await interaction.user.send(f"🎁 RAVN EVENT WINNER\\n\\nYou won **{self.game.prize}** from the Dino Guess event!\\n\\n🎟️ **Gift Card Code:** `{self.game.gift_card_code}`\\n\\nKeep this code private.")
                gift_message = "\\n📩 Your gift card code has been sent to your DMs."
            except discord.Forbidden:
                gift_message = "\\n⚠️ I could not DM you. Please enable DMs from server members."
        if self.game.message:
            embed = ravn_embed(
                "🦖 DINO GUESS EVENT — WON",
                f"🏆 **Winner:** {interaction.user.mention}\n🦖 **Dinosaur:** **{self.game.answer}**\n🎁 **Prize:** **{self.game.prize}**",
                colour=SUCCESS,
                footer="RAVN Server Manager • Community Events",
            )
            await self.game.message.edit(embed=brand_embed(embed, bot_avatar_url(interaction.client)), view=self.game)
        await interaction.response.send_message(
            f"🎉 Correct! You won **{self.game.prize}**.{gift_message}",
            ephemeral=True,
        )


class DinoGuessView(discord.ui.View):
    def __init__(self, answer: str, prize: str, gift_card_code: str | None = None) -> None:
        super().__init__(timeout=None)
        self.answer = answer.strip()
        self.prize = prize
        self.gift_card_code = gift_card_code
        self.winner_id: int | None = None
        self.message: discord.Message | None = None

    @discord.ui.button(label="GUESS THE DINO", emoji="🦖", style=discord.ButtonStyle.primary)
    async def guess_dino(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.winner_id is not None:
            await interaction.response.send_message("🏆 This event has already been won.", ephemeral=True)
            return
        await interaction.response.send_modal(DinoGuessModal(self))


class VaultCodeModal(discord.ui.Modal, title="Crack the Vault"):
    code = discord.ui.TextInput(
        label="Enter the vault code",
        placeholder="Enter the code you think opens the vault",
        max_length=100,
    )

    def __init__(self, game: "VaultCodeView") -> None:
        super().__init__()
        self.game = game

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.game.winner_id is not None:
            await interaction.response.send_message("🔒 The vault has already been opened.", ephemeral=True)
            return
        if self.code.value.strip().casefold() != self.game.code.casefold():
            await interaction.response.send_message("❌ Incorrect code. The vault remains locked!", ephemeral=True)
            return
        self.game.winner_id = interaction.user.id
        self.game.stop()
        gift_message = ""
        if self.game.gift_card_code:
            try:
                await interaction.user.send(f"🎁 RAVN EVENT WINNER\\n\\nYou won **{self.game.prize}** from the Vault event!\\n\\n🎟️ **Gift Card Code:** `{self.game.gift_card_code}`\\n\\nKeep this code private.")
                gift_message = "\\n📩 Your gift card code has been sent to your DMs."
            except discord.Forbidden:
                gift_message = "\\n⚠️ I could not DM you. Please enable DMs from server members."
        if self.game.message:
            embed = ravn_embed(
                "🔓 VAULT CODE EVENT — CRACKED",
                f"🏆 **Winner:** {interaction.user.mention}\n🔐 **Vault code:** **{self.game.code}**\n🎁 **Prize:** **{self.game.prize}**",
                colour=SUCCESS,
                footer="RAVN Server Manager • Community Events",
            )
            await self.game.message.edit(embed=brand_embed(embed, bot_avatar_url(interaction.client)), view=self.game)
        await interaction.response.send_message(
            f"🎉 Vault cracked! You won **{self.game.prize}**.{gift_message}",
            ephemeral=True,
        )


class VaultCodeView(discord.ui.View):
    def __init__(self, code: str, prize: str, gift_card_code: str | None = None) -> None:
        super().__init__(timeout=None)
        self.code = code.strip()
        self.prize = prize
        self.gift_card_code = gift_card_code
        self.winner_id: int | None = None
        self.message: discord.Message | None = None

    @discord.ui.button(label="CRACK THE VAULT", emoji="🔐", style=discord.ButtonStyle.success)
    async def crack_vault(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.winner_id is not None:
            await interaction.response.send_message("🔒 The vault has already been opened.", ephemeral=True)
            return
        await interaction.response.send_modal(VaultCodeModal(self))


ACTIVE_GIVEAWAYS: list[GiveawayView] = []


class EventRSVPView(discord.ui.View):
    def __init__(self, event_name: str) -> None:
        super().__init__(timeout=None)
        self.event_name = event_name
        self.attendees: set[int] = set()

    @discord.ui.button(label="RSVP", emoji="🎟️", style=discord.ButtonStyle.primary, custom_id="ravn:event:rsvp")
    async def rsvp(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id in self.attendees:
            self.attendees.remove(interaction.user.id)
            await interaction.response.send_message("You have been removed from the RSVP list.", ephemeral=True)
        else:
            self.attendees.add(interaction.user.id)
            await interaction.response.send_message(f"🎟️ RSVP confirmed for **{self.event_name}**. Attendees: **{len(self.attendees)}**.", ephemeral=True)



def register(bot: discord.Client) -> None:
    @bot.tree.command(name="help", description="Open the RAVN Server Manager command centre.")
    async def help_command(interaction: discord.Interaction) -> None:
        embed = ravn_embed(
            "🤖 RAVN SERVER MANAGER",
            "Your central command centre for the RAVN ARK Survival Ascended community.",
            colour=RAVN_PURPLE,
            footer="RAVN Server Manager • Command Centre",
        )
        embed.add_field(name="🎫 Support", value="/ticket — private support panel", inline=True)
        embed.add_field(name="🎉 Community", value="/giveaway • /event • /dino-event • /vault-event • /recruit", inline=True)
        embed.add_field(name="📢 Server", value="/announce • /patchnotes", inline=True)
        embed.add_field(name="🛡️ Moderation", value="/warn • /timeout • /kick • /ban • /unban • /clear", inline=False)
        embed.add_field(name="⚖️ Punishments", value="/punish — create a formal tribe punishment record with evidence", inline=False)
        embed.add_field(name="⚙️ Management", value="/setup-server — repair and provision the server", inline=False)
        await interaction.response.send_message(embed=brand_embed(embed, bot_avatar_url(interaction.client)), ephemeral=True)

    class StaffDashboardView(discord.ui.View):
        def __init__(self) -> None:
            super().__init__(timeout=None)

        async def _staff_only(self, interaction: discord.Interaction) -> bool:
            if isinstance(interaction.user, discord.Member) and (interaction.user.guild_permissions.manage_guild or interaction.user.guild_permissions.administrator or _is_staff(interaction.user)):
                return True
            await interaction.response.send_message("You do not have permission to use the staff dashboard.", ephemeral=True)
            return False

        @discord.ui.button(label="Tickets", emoji="🎫", style=discord.ButtonStyle.primary, row=0)
        async def tickets(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            if not await self._staff_only(interaction): return
            channels = [channel.mention for channel in interaction.guild.text_channels if channel.topic and "ticket_owner:" in channel.topic and "state:closed" not in channel.topic] if interaction.guild else []
            await interaction.response.send_message("🎫 **Open Tickets**\n" + ("\n".join(channels) if channels else "No open tickets."), ephemeral=True)

        @discord.ui.button(label="Punishments", emoji="⚖️", style=discord.ButtonStyle.secondary, row=0)
        async def punishments(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            if not await self._staff_only(interaction): return
            await interaction.response.send_message("⚖️ Use /punishments to search punishment history or /punishment-remove to void a record.", ephemeral=True)

        @discord.ui.button(label="Reports", emoji="🚨", style=discord.ButtonStyle.danger, row=0)
        async def reports(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            if not await self._staff_only(interaction): return
            await interaction.response.send_message("🚨 Use /report to create a private player report.", ephemeral=True)

        @discord.ui.button(label="Announcements", emoji="📢", style=discord.ButtonStyle.secondary, row=1)
        async def announcements(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            if not await self._staff_only(interaction): return
            channel = _find_channel(interaction.guild, "📢・announcements") if interaction.guild else None
            destination = channel.mention if channel else "not configured"
            await interaction.response.send_message(f"📢 Announcements: {destination}", ephemeral=True)

        @discord.ui.button(label="Giveaways", emoji="🎉", style=discord.ButtonStyle.secondary, row=1)
        async def giveaways(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            if not await self._staff_only(interaction): return
            await interaction.response.send_message("🎉 Use /giveaway to start a giveaway.", ephemeral=True)

        @discord.ui.button(label="Events", emoji="🎪", style=discord.ButtonStyle.secondary, row=1)
        async def events(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            if not await self._staff_only(interaction): return
            await interaction.response.send_message("🎪 Use /event to publish an event.", ephemeral=True)

        @discord.ui.button(label="Statistics", emoji="📊", style=discord.ButtonStyle.secondary, row=2)
        async def statistics(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            if not await self._staff_only(interaction): return
            guild = interaction.guild
            await interaction.response.send_message(f"📊 **Server Statistics**\nMembers: **{guild.member_count if guild else 0}**\nChannels: **{len(guild.channels) if guild else 0}**\nRoles: **{len(guild.roles) if guild else 0}**", ephemeral=True)

        @discord.ui.button(label="Management", emoji="🔧", style=discord.ButtonStyle.success, row=2)
        async def management(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
            if not await self._staff_only(interaction): return
            await interaction.response.send_message("🔧 **Management**\nUse /announce, /patchnotes, /event, /giveaway, /punish, /clear and /setup-server.", ephemeral=True)

    @bot.tree.command(name="staff-panel", description="Open the RAVN staff control centre.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def staff_panel(interaction: discord.Interaction) -> None:
        if not interaction.guild: return
        open_tickets = sum(1 for channel in interaction.guild.text_channels if channel.topic and "ticket_owner:" in channel.topic and "state:closed" not in channel.topic)
        embed = ravn_embed("🦅 RAVN CONTROL CENTRE", "Central staff dashboard for your ARK Survival Ascended community.", colour=RAVN_PURPLE, footer="RAVN Server Manager • Staff Control Centre")
        embed.add_field(name="👥 MEMBERS", value=f"**{interaction.guild.member_count or 0:,}**", inline=True)
        embed.add_field(name="🎫 OPEN TICKETS", value=f"**{open_tickets}**", inline=True)
        embed.add_field(name="⚖️ PUNISHMENTS", value="**Use /punishments**", inline=True)
        embed.add_field(name="🚨 REPORTS", value="**Use /report**", inline=True)
        embed.add_field(name="🎪 EVENTS", value="**Use /event**", inline=True)
        embed.add_field(name="🟢 BOT STATUS", value="**ONLINE**", inline=True)
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", value="🎫 Tickets     ⚖️ Punishments     🚨 Reports\n📢 Announcements     🎉 Giveaways     🎪 Events\n📊 Statistics     🔧 Server Management", inline=False)
        await interaction.response.send_message(embed=brand_embed(embed, bot_avatar_url(interaction.client)), view=StaffDashboardView(), ephemeral=True)
    @bot.tree.command(name="punish", description="Create a formal tribe punishment record with evidence.")
    @discord.app_commands.check(_can_issue_punishment)
    async def punish(
        interaction: discord.Interaction,
        tribe_name: str,
        rule_broken: str,
        punishment: str,
        evidence_1: discord.Attachment | None = None,
        evidence_2: discord.Attachment | None = None,
        evidence_3: discord.Attachment | None = None,
    ) -> None:
        if not interaction.guild:
            return

        channel = _find_channel(interaction.guild, "⛔・punishments")
        if not channel:
            await interaction.response.send_message(
                "The ⛔・punishments channel does not exist. Please create it in the staff section.",
                ephemeral=True,
            )
            return

        evidence = [item for item in (evidence_1, evidence_2, evidence_3) if item]
        case_id = create_case(interaction.guild.id, "punishment", tribe_name, rule_broken, punishment, interaction.user.id, "\n".join(item.url for item in evidence))
        evidence_lines = []
        for index, attachment in enumerate(evidence, start=1):
            evidence_lines.append(f"**Evidence {index}:** [View attachment]({attachment.url})")
        evidence_text = "\n".join(evidence_lines) if evidence_lines else "No screenshots or videos attached."

        embed = ravn_embed(
            f"⚖️ RAVN PUNISHMENT • CASE-{case_id:06d}",
            f"A formal punishment has been issued against **{tribe_name}**.",
            colour=RAVN_PURPLE,
            footer="RAVN Server Manager • Punishment System",
        )
        embed.add_field(name="🏹 Tribe", value=tribe_name, inline=True)
        embed.add_field(name="📜 Rule Broken", value=rule_broken, inline=True)
        embed.add_field(name="🔨 Punishment", value=punishment, inline=False)
        embed.add_field(name="👮 Issued By", value=f"{interaction.user.mention}\n`{interaction.user}`", inline=True)
        embed.add_field(name="🕒 Issued At", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", inline=True)
        embed.add_field(name="📎 Evidence", value=evidence_text, inline=False)

        first_image = next(
            (
                attachment
                for attachment in evidence
                if attachment.content_type and attachment.content_type.startswith("image/")
            ),
            None,
        )
        if first_image:
            embed.set_image(url=first_image.url)

        await channel.send(
            embed=brand_embed(embed, bot_avatar_url(interaction.client)),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        await interaction.response.send_message(
            f"✅ Punishment record created in {channel.mention}.",
            ephemeral=True,
        )

    @bot.tree.command(name="recruit", description="Open a form to publish a tribe recruitment post.")
    async def recruit(interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(RecruitmentModal())

    @bot.tree.command(name="patchnotes", description="Publish server patch notes to the server patch channel.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def patchnotes(interaction: discord.Interaction, version: str, changes: str) -> None:
        if not interaction.guild:
            return
        channel = _find_channel(interaction.guild, "⚙️・server-patch")
        if not channel:
            await interaction.response.send_message("The ⚙️・server-patch channel does not exist. Please create it before using /patchnotes.", ephemeral=True)
            return
        await channel.send(
            embed=brand_embed(patch_notes_embed(version, changes), bot_avatar_url(interaction.client))
        )
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
        ACTIVE_GIVEAWAYS.append(view)
        embed = ravn_embed(
            "🎉 RAVN GIVEAWAY",
            f"🏆 **PRIZE**\n{prize}\n\n👥 **WINNERS**\n{winners}\n\n⏰ **ENDS**\n<t:{int(ends_at)}:R>\n\nPress **🎉 ENTER GIVEAWAY** below to enter.",
            colour=RAVN_PURPLE,
            footer="RAVN Server Manager • Giveaways",
        )
        await interaction.response.send_message(
            embed=brand_embed(embed, bot_avatar_url(interaction.client)),
            view=view,
        )
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
        channel = _find_channel(interaction.guild, "🎪・server-events") or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return
        await channel.send(
            embed=brand_embed(
                event_embed(name, date, time, description, prize, location, requirements),
                bot_avatar_url(interaction.client),
            ),
            view=EventRSVPView(name),
        )
        await interaction.response.send_message(f"Event posted in {channel.mention}.", ephemeral=True)

    @bot.tree.command(name="dino-event", description="Start a first-correct dinosaur guessing event.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def dino_event(interaction: discord.Interaction, answer: str, prize: str = "Store Gift Card") -> None:
        if not interaction.guild:
            return
        channel = _find_channel(interaction.guild, "🎪・server-events") or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("The event channel is not available.", ephemeral=True)
            return
        view = DinoGuessView(answer, prize)
        embed = ravn_embed(
            "🦖 RAVN DINO GUESS",
            f"🧩 **A mystery dinosaur is hidden!**\n\nBe the first person to guess it correctly and win:\n🎁 **{prize}**\n\nPress **🦖 GUESS THE DINO** to submit your answer.\n\n⚠️ One correct answer wins the event.",
            colour=RAVN_PURPLE,
            footer="RAVN Server Manager • Community Events",
        )
        message = await channel.send(embed=brand_embed(embed, bot_avatar_url(interaction.client)), view=view)
        view.message = message
        await interaction.response.send_message(f"🦖 Dino guess event posted in {channel.mention}.", ephemeral=True)

    async def _post_scheduled_event(guild: discord.Guild, event_type: str) -> None:
        channel = _find_channel(guild, "🎪・server-events")
        if not channel:
            logger.warning("Scheduled event skipped for guild %s: 🎪・server-events not found", guild.id)
            return

        if event_type == "vault":
            code = random.randint(1, 500)
            gift_value = random.choice(VAULT_GIFT_CARD_VALUES)
            view = VaultCodeView(str(code), f"{gift_value} Gift Card", _gift_code_for("vault"))
            embed = ravn_embed(
                "🔐 RAVN VAULT CHALLENGE",
                "🏦 **THE VAULT IS LOCKED**\n\nA random vault code between **1 and 500** has been generated.\n\nBe the **first** person to enter the correct code and win:\n🎁 **Store Gift Card**\n\nPress **🔐 CRACK THE VAULT** to submit your guess.\n\n⏰ A new challenge runs every **4 hours**.\n⚠️ One correct answer wins.",
                colour=RAVN_PURPLE,
                footer="RAVN Server Manager • Automatic 4-Hour Events",
            )
        else:
            answer = random.choice(DINO_EVENT_ANSWERS)
            scrambled = _scramble_dino(answer)
            gift_value = random.choice(DINO_GIFT_CARD_VALUES)
            view = DinoGuessView(answer, f"{gift_value} Gift Card", _gift_code_for("dino"))
            embed = ravn_embed(
                "🦖 RAVN DINO GUESS",
                f"🧩 **UNSCRAMBLE THE DINOSAUR**\\n\\n**{scrambled.upper()}**\\n\\nThe dinosaur's letters have been mixed up. Can you work out the name?\\n\\nBe the **first** person to guess it correctly and win:\\n🎁 **{gift_value} Gift Card**\\n\\nPress **🦖 GUESS THE DINO** to submit your guess.\\n\\n⏰ A new challenge runs every **4 hours**.\\n⚠️ One correct answer wins.",
                colour=RAVN_PURPLE,
                footer="RAVN Server Manager • Automatic 4-Hour Events",
            )

        message = await channel.send(
            embed=brand_embed(embed, bot_avatar_url(bot)),
            view=view,
        )
        view.message = message

    async def _automatic_event_loop() -> None:
        global EVENT_SCHEDULER_STARTED
        if EVENT_SCHEDULER_STARTED:
            return
        EVENT_SCHEDULER_STARTED = True
        await bot.wait_until_ready()
        event_type = "vault"
        while not bot.is_closed():
            try:
                for guild in bot.guilds:
                    await _post_scheduled_event(guild, event_type)
                event_type = "dino" if event_type == "vault" else "vault"
                await asyncio.sleep(EVENT_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Automatic 4-hour event loop failed")
                await asyncio.sleep(60)

    if not any(task.get_name() == "ravn-automatic-events" for task in asyncio.all_tasks()):
        task = asyncio.create_task(_automatic_event_loop(), name="ravn-automatic-events")

    @bot.tree.command(name="vault-event", description="Start a first-correct vault code event.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def vault_event(interaction: discord.Interaction, code: str, prize: str = "Store Gift Card") -> None:
        if not interaction.guild:
            return
        channel = _find_channel(interaction.guild, "🎪・server-events") or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("The event channel is not available.", ephemeral=True)
            return
        view = VaultCodeView(code, prize)
        embed = ravn_embed(
            "🔐 RAVN VAULT CODE",
            f"🏦 **The vault is locked!**\n\nBe the first person to crack the code and win:\n🎁 **{prize}**\n\nPress **🔐 CRACK THE VAULT** to submit a code.\n\n⚠️ One correct code wins the event.",
            colour=RAVN_PURPLE,
            footer="RAVN Server Manager • Community Events",
        )
        message = await channel.send(embed=brand_embed(embed, bot_avatar_url(interaction.client)), view=view)
        view.message = message
        await interaction.response.send_message(f"🔐 Vault code event posted in {channel.mention}.", ephemeral=True)

    @bot.tree.command(name="announce", description="Publish a staff announcement.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def announce(interaction: discord.Interaction, title: str, body: str) -> None:
        if not interaction.guild:
            return
        channel = _find_channel(interaction.guild, "📢・announcements") or interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return
        await channel.send(
            embed=brand_embed(announcements_embed(title, body), bot_avatar_url(interaction.client))
        )
        await interaction.response.send_message(f"Announcement posted in {channel.mention}.", ephemeral=True)


    @bot.tree.command(name="server-stats", description="Show detailed RAVN server statistics.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def server_stats(interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        guild = interaction.guild
        bots = sum(1 for member in guild.members if member.bot)
        humans = max(0, (guild.member_count or 0) - bots)
        open_tickets = sum(1 for ch in guild.text_channels if ch.topic and "ticket_owner:" in ch.topic and "state:closed" not in ch.topic)
        embed = ravn_embed(
            "📊 RAVN SERVER STATISTICS",
            f"👥 Humans: **{humans:,}**\n🤖 Bots: **{bots:,}**\n💬 Text channels: **{len(guild.text_channels):,}**\n🔊 Voice channels: **{len(guild.voice_channels):,}**\n📁 Categories: **{len(guild.categories):,}**\n🎭 Roles: **{len(guild.roles):,}**\n🎫 Open tickets: **{open_tickets:,}**",
            colour=RAVN_PURPLE,
            footer="RAVN Server Manager • Statistics",
        )
        await interaction.response.send_message(embed=brand_embed(embed, bot_avatar_url(interaction.client)), ephemeral=True)

    @bot.tree.command(name="giveaway-status", description="Show active RAVN giveaways.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway_status(interaction: discord.Interaction) -> None:
        active = [g for g in ACTIVE_GIVEAWAYS if g.message and g.ends_at > datetime.now(timezone.utc).timestamp()]
        if not active:
            await interaction.response.send_message("🎉 There are no active giveaways.", ephemeral=True)
            return
        embed = ravn_embed("🎉 ACTIVE GIVEAWAYS", "Current giveaways managed by RAVN.", colour=RAVN_PURPLE)
        for g in active:
            embed.add_field(name=g.prize, value=f"👥 Winners: {g.winners}\n🎟️ Entries: {len(g.entries)}\n⏰ Ends: <t:{int(g.ends_at)}:R>", inline=False)
        await interaction.response.send_message(embed=brand_embed(embed, bot_avatar_url(interaction.client)), ephemeral=True)
