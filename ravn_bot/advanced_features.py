from __future__ import annotations
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
import discord
from discord import app_commands
from .embeds import ARK_BLUE, DANGER, RAVN_PURPLE, SUCCESS, WARNING, brand_embed, bot_avatar_url, ravn_embed

DB = Path(__file__).resolve().parent / "ravn.sqlite3"

def db():
    c=sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS ravn_bounties(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER,target TEXT,reward INTEGER,reason TEXT,claimed_by INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS ravn_rewards(guild_id INTEGER,user_id INTEGER,points INTEGER DEFAULT 0,daily_at TEXT,PRIMARY KEY(guild_id,user_id))")
    c.execute("CREATE TABLE IF NOT EXISTS ravn_staff_activity(guild_id INTEGER,user_id INTEGER,actions INTEGER DEFAULT 0,last_action TEXT,PRIMARY KEY(guild_id,user_id))")
    c.execute("CREATE TABLE IF NOT EXISTS ravn_notifications(guild_id INTEGER,kind TEXT,channel_id INTEGER,role_id INTEGER,enabled INTEGER DEFAULT 1,PRIMARY KEY(guild_id,kind))")
    c.commit()
    return c

def mgmt(m):
    return isinstance(m,discord.Member) and (m.guild_permissions.administrator or m.guild_permissions.manage_guild or any(r.name in {"⚡ Server Manager","🛡️ Co-Owner","👑 Owner"} for r in m.roles))

def add_points(gid,uid,n):
    c=db(); c.execute("INSERT INTO ravn_rewards(guild_id,user_id,points) VALUES(?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET points=points+?",(gid,uid,n,n)); c.commit(); c.close()

def ch(g,n): return discord.utils.get(g.text_channels,name=n)

def dash(g):
    h=sum(not m.bot for m in g.members); b=sum(m.bot for m in g.members)
    t=sum(1 for x in g.text_channels if x.topic and "ticket_owner:" in x.topic and "state:closed" not in x.topic)
    e=ravn_embed("📊 RAVN SERVER DASHBOARD","Live management overview.",colour=RAVN_PURPLE,footer="RAVN Server Manager • Dashboard")
    e.add_field(name="👥 MEMBERS",value="Humans: **{}**\nBots: **{}**".format(h,b),inline=True)
    e.add_field(name="🎫 TICKETS",value="Open: **{}**".format(t),inline=True)
    e.add_field(name="🎭 ROLES",value="**{}**".format(len(g.roles)),inline=True)
    e.add_field(name="💬 CHANNELS",value="Text: **{}**\nVoice: **{}**".format(len(g.text_channels),len(g.voice_channels)),inline=True)
    e.add_field(name="📁 CATEGORIES",value="**{}**".format(len(g.categories)),inline=True)
    e.add_field(name="🟢 RAVN",value="**ONLINE**",inline=True)
    return e

class DashView(discord.ui.View):
    def __init__(self): super().__init__(timeout=180)
    @discord.ui.button(label="Refresh",emoji="🔄",style=discord.ButtonStyle.primary)
    async def refresh(self,i,b):
        if i.guild: await i.response.edit_message(embed=brand_embed(dash(i.guild),bot_avatar_url(i.client)),view=self)
    @discord.ui.button(label="Tickets",emoji="🎫",style=discord.ButtonStyle.secondary)
    async def tickets(self,i,b):
        if i.guild:
            n=sum(1 for x in i.guild.text_channels if x.topic and "ticket_owner:" in x.topic and "state:closed" not in x.topic)
            await i.response.send_message("🎫 Open tickets: **{}**".format(n),ephemeral=True)
    @discord.ui.button(label="Close",emoji="✖️",style=discord.ButtonStyle.secondary)
    async def close(self,i,b): await i.response.edit_message(view=None)

class BountyModal(discord.ui.Modal,title="Create RAVN Bounty"):
    target=discord.ui.TextInput(label="Player / Tribe",max_length=100)
    reward=discord.ui.TextInput(label="Reward points",placeholder="100",max_length=10)
    reason=discord.ui.TextInput(label="Objective",style=discord.TextStyle.paragraph,max_length=800)
    async def on_submit(self,i):
        if not i.guild or not mgmt(i.user):
            await i.response.send_message("Only management can create bounties.",ephemeral=True); return
        try: r=max(1,int(self.reward.value))
        except ValueError:
            await i.response.send_message("Reward must be a whole number.",ephemeral=True); return
        c=db(); cur=c.execute("INSERT INTO ravn_bounties(guild_id,target,reward,reason) VALUES(?,?,?,?)",(i.guild.id,self.target.value.strip(),r,self.reason.value.strip())); c.commit(); num=cur.lastrowid; c.close()
        out=ch(i.guild,"🎯・bounties")
        if out:
            e=ravn_embed("🎯 RAVN BOUNTY • #{}".format(num),"**Target:** {}\n**Reward:** **{} points**\n**Objective:** {}".format(self.target.value.strip(),r,self.reason.value.strip()),colour=DANGER)
            await out.send(embed=brand_embed(e,bot_avatar_url(i.client)))
        await i.response.send_message("🎯 Bounty **#{}** created.".format(num),ephemeral=True)

def register(bot):
    @bot.tree.command(name="bounty",description="Create an ARK PvP bounty.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def bounty(i): await i.response.send_modal(BountyModal())

    @bot.tree.command(name="bounties",description="List active bounties.")
    async def bounties(i):
        if not i.guild:return
        c=db(); rows=c.execute("SELECT id,target,reward,reason FROM ravn_bounties WHERE guild_id=? AND claimed_by IS NULL ORDER BY id DESC LIMIT 10",(i.guild.id,)).fetchall(); c.close()
        if not rows: await i.response.send_message("🎯 No active bounties.",ephemeral=True); return
        e=ravn_embed("🎯 ACTIVE BOUNTIES","Current objectives.",colour=DANGER)
        for r in rows:e.add_field(name="#{} • {}".format(r[0],r[1]),value="💰 {} points\n{}".format(r[2],r[3]),inline=False)
        await i.response.send_message(embed=brand_embed(e,bot_avatar_url(i.client)))

    @bot.tree.command(name="bounty-claim",description="Verify a bounty and award points.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def bounty_claim(i,case_number:int,winner:discord.Member|None=None):
        if not i.guild or not mgmt(i.user): await i.response.send_message("Management only.",ephemeral=True); return
        c=db(); r=c.execute("SELECT reward FROM ravn_bounties WHERE guild_id=? AND id=? AND claimed_by IS NULL",(i.guild.id,case_number)).fetchone()
        if not r: c.close(); await i.response.send_message("Bounty not found or already claimed.",ephemeral=True); return
        m=winner or i.user; c.execute("UPDATE ravn_bounties SET claimed_by=? WHERE guild_id=? AND id=?",(m.id,i.guild.id,case_number)); c.commit(); c.close(); add_points(i.guild.id,m.id,r[0])
        await i.response.send_message("🏆 Bounty #{} verified for {}: +{} points.".format(case_number,m.mention,r[0]),ephemeral=True)

    @bot.tree.command(name="rewards",description="View your RAVN points.")
    async def rewards(i):
        if not i.guild:return
        c=db(); r=c.execute("SELECT points FROM ravn_rewards WHERE guild_id=? AND user_id=?",(i.guild.id,i.user.id)).fetchone(); c.close()
        e=ravn_embed("🏆 RAVN REWARDS","You have **{} points**.".format(r[0] if r else 0),colour=RAVN_PURPLE)
        await i.response.send_message(embed=brand_embed(e,bot_avatar_url(i.client)),ephemeral=True)

    @bot.tree.command(name="daily",description="Claim your daily RAVN reward.")
    async def daily(i):
        if not i.guild:return
        now=datetime.now(timezone.utc); c=db(); r=c.execute("SELECT points,daily_at FROM ravn_rewards WHERE guild_id=? AND user_id=?",(i.guild.id,i.user.id)).fetchone()
        if r and r[1] and (now-datetime.fromisoformat(r[1])).total_seconds()<86400:
            await i.response.send_message("⏳ Your daily reward is ready <t:{}:R>.".format(int((datetime.fromisoformat(r[1])+timedelta(days=1)).timestamp())),ephemeral=True); c.close(); return
        p=(r[0] if r else 0)+25
        c.execute("INSERT INTO ravn_rewards(guild_id,user_id,points,daily_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET points=?,daily_at=?",(i.guild.id,i.user.id,p,now.isoformat(),p,now.isoformat())); c.commit(); c.close()
        await i.response.send_message("🎁 Daily reward claimed: **+25 points**.",ephemeral=True)

    @bot.tree.command(name="ticket-stats",description="Show live ticket workload.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_stats(i):
        if not i.guild:return
        t=[x for x in i.guild.text_channels if x.topic and "ticket_owner:" in x.topic and "state:closed" not in x.topic]
        claimed=sum("claimed_by:" in x.topic and "claimed_by:unclaimed" not in x.topic for x in t)
        e=ravn_embed("🎫 TICKET OPERATIONS","Open: **{}**\nClaimed: **{}**\nUnclaimed: **{}**".format(len(t),claimed,len(t)-claimed),colour=ARK_BLUE)
        await i.response.send_message(embed=brand_embed(e,bot_avatar_url(i.client)),ephemeral=True)

    @bot.tree.command(name="dashboard",description="Open the live RAVN management dashboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def dashboard(i):
        if i.guild: await i.response.send_message(embed=brand_embed(dash(i.guild),bot_avatar_url(i.client)),view=DashView(),ephemeral=True)

    @bot.tree.command(name="health",description="Check RAVN health and core channels.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def health(i):
        if not i.guild:return
        names=("🎉・discord-events","🎫・ticket-logs","📊・staff-logs","📢・announcements","⚙️・server-patch","🔒・verify")
        missing=[n for n in names if not ch(i.guild,n)]
        e=ravn_embed("🟢 RAVN HEALTH CHECK","Latency: **{}ms**\nMissing core channels: **{}**".format(round(bot.latency*1000),len(missing)),colour=SUCCESS if not missing else WARNING)
        if missing:e.add_field(name="⚠️ Missing",value="\n".join(missing),inline=False)
        await i.response.send_message(embed=brand_embed(e,bot_avatar_url(i.client)),ephemeral=True)

    @bot.tree.command(name="cleanup-tickets",description="Remove old closed tickets.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def cleanup_tickets(i,days:app_commands.Range[int,1,365]=30):
        if not i.guild:return
        await i.response.defer(ephemeral=True); cutoff=datetime.now(timezone.utc)-timedelta(days=days); n=0
        for x in list(i.guild.text_channels):
            if x.topic and "state:closed" in x.topic and x.created_at<cutoff:
                try: await x.delete(reason="RAVN housekeeping"); n+=1
                except discord.HTTPException: pass
        await i.followup.send("🧹 Removed **{}** old closed ticket(s).".format(n),ephemeral=True)

    @bot.tree.command(name="verify-check",description="Check Survivor and Unverified role configuration.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def verify_check(i):
        if not i.guild:return
        me=i.guild.me; s=discord.utils.get(i.guild.roles,name="Survivor"); u=discord.utils.get(i.guild.roles,name="Unverified"); p=[]
        if not s:p.append("Missing Survivor role.")
        if not u:p.append("Missing Unverified role.")
        if me and s and s>=me.top_role:p.append("Bot role must be above Survivor.")
        if me and u and u>=me.top_role:p.append("Bot role must be above Unverified.")
        e=ravn_embed("🛡️ VERIFICATION CHECK","✅ Configuration looks correct." if not p else "⚠️ Attention required:\n"+"\n".join("• "+x for x in p),colour=SUCCESS if not p else WARNING)
        await i.response.send_message(embed=brand_embed(e,bot_avatar_url(i.client)),ephemeral=True)

    @bot.tree.command(name="notify-setup",description="Configure smart notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def notify_setup(i,kind:str,channel:discord.TextChannel,role:discord.Role|None=None):
        if not i.guild:return
        if kind not in {"events","giveaways","status","patches"}:
            await i.response.send_message("Kind must be events, giveaways, status or patches.",ephemeral=True); return
        c=db(); c.execute("INSERT INTO ravn_notifications(guild_id,kind,channel_id,role_id) VALUES(?,?,?,?) ON CONFLICT(guild_id,kind) DO UPDATE SET channel_id=?,role_id=?,enabled=1",(i.guild.id,kind,channel.id,role.id if role else None,channel.id,role.id if role else None)); c.commit(); c.close()
        await i.response.send_message("🔔 {} notifications configured for {}.".format(kind,channel.mention),ephemeral=True)

    @bot.tree.command(name="notify-test",description="Test smart notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def notify_test(i,kind:str="events"):
        if not i.guild:return
        c=db(); r=c.execute("SELECT channel_id,role_id,enabled FROM ravn_notifications WHERE guild_id=? AND kind=?",(i.guild.id,kind)).fetchone(); c.close()
        if r and r[2]:
            out=i.guild.get_channel(r[0]); role=i.guild.get_role(r[1]) if r[1] else None
            if isinstance(out,discord.TextChannel): await out.send("{}🔔 RAVN notification test.".format(role.mention+" " if role else ""))
        await i.response.send_message("🔔 Notification test completed.",ephemeral=True)

    @bot.tree.command(name="moderation-tools",description="Open the advanced moderation toolkit.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def moderation_tools(i):
        e=ravn_embed("🛡️ ADVANCED MODERATION","Use the existing warn/kick/ban/timeout/clear/unban commands plus the persistent punishment case system.\n\nRAVN also records staff command activity and provides /health monitoring.",colour=DANGER)
        await i.response.send_message(embed=brand_embed(e,bot_avatar_url(i.client)),ephemeral=True)

    async def command_complete(i,command):
        if not i.guild or not isinstance(i.user,discord.Member):return
        c=db(); now=datetime.now(timezone.utc).isoformat()
        c.execute("INSERT INTO ravn_staff_activity(guild_id,user_id,actions,last_action) VALUES(?,?,1,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET actions=actions+1,last_action=?",(i.guild.id,i.user.id,now,now)); c.commit(); c.close()
    bot.add_listener(command_complete,"on_app_command_completion")
