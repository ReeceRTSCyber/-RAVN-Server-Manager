from __future__ import annotations

import logging

import discord

from .embeds import RAVN_PURPLE, brand_embed, bot_avatar_url, ravn_embed

logger = logging.getLogger(__name__)

SURVIVOR_ROLE_NAME = "🦖 Survivor"
VERIFY_LOG_CHANNEL_NAMES = {"📊・staff-logs", "📜・mod-logs"}

def _find_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    for name in VERIFY_LOG_CHANNEL_NAMES:
        channel = discord.utils.get(guild.text_channels, name=name)
        if channel:
            return channel
    return None

class VerifyView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="VERIFY", emoji="✅", style=discord.ButtonStyle.success, custom_id="ravn:verify:survivor")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Verification can only be completed inside the RAVN server.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name=SURVIVOR_ROLE_NAME)
        if not role:
            await interaction.response.send_message(f"The {SURVIVOR_ROLE_NAME} role could not be found. Please contact staff.", ephemeral=True)
            return
        if interaction.guild.me and role >= interaction.guild.me.top_role:
            await interaction.response.send_message("I cannot assign the Survivor role. Move the RAVN bot role above Survivor in Server Settings → Roles.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("✅ You are already verified as a Survivor.", ephemeral=True)
            return
        try:
            await interaction.user.add_roles(role, reason="RAVN member verification")
        except discord.Forbidden:
            await interaction.response.send_message("Discord denied the role update. Check that RAVN has Manage Roles and that its bot role is above Survivor.", ephemeral=True)
            return
        except discord.HTTPException:
            logger.exception("Failed to verify member %s", interaction.user.id)
            await interaction.response.send_message("Verification failed temporarily. Please try again in a moment.", ephemeral=True)
            return
        log_channel = _find_log_channel(interaction.guild)
        if log_channel:
            embed = ravn_embed("🛡️ MEMBER VERIFIED", f"{interaction.user.mention} has completed server verification.", colour=RAVN_PURPLE, footer="RAVN Server Manager • Verification")
            embed.add_field(name="👤 Member", value=f"{interaction.user.mention}\n`{interaction.user}`", inline=True)
            embed.add_field(name="🎭 Role Given", value=role.mention, inline=True)
            await log_channel.send(embed=brand_embed(embed, bot_avatar_url(interaction.client)), allowed_mentions=discord.AllowedMentions.none())
        await interaction.response.send_message(f"✅ Verification complete! You have been given {role.mention}. Welcome to RAVN!", ephemeral=True)

def verification_embed() -> discord.Embed:
    embed = ravn_embed("🛡️ RAVN VERIFICATION", "Welcome to the RAVN ARK Survival Ascended community!\n\nBefore accessing the community, click **VERIFY** below to confirm that you are a member of the server.\n\nOnce verified, you will receive the **🦖 Survivor** role.", colour=RAVN_PURPLE, footer="RAVN Server Manager • Member Verification")
    embed.add_field(name="✅ What happens when I verify?", value="You will automatically receive the 🦖 Survivor role.", inline=False)
    embed.add_field(name="⚠️ Need help?", value="If verification does not work, contact a member of staff.", inline=False)
    return embed

def register(bot: discord.Client) -> None:
    bot.add_view(VerifyView())

    @bot.tree.command(name="verify-panel", description="Post the RAVN Survivor verification panel.")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.checks.has_permissions(manage_guild=True)
    async def verify_panel(interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Run this command in the channel where you want the verification panel.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name=SURVIVOR_ROLE_NAME)
        if not role:
            await interaction.response.send_message(f"I could not find the {SURVIVOR_ROLE_NAME} role.", ephemeral=True)
            return
        await interaction.response.send_message(embed=brand_embed(verification_embed(), bot_avatar_url(interaction.client)), view=VerifyView())
