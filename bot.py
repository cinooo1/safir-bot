import discord
from discord.ext import commands
from collections import defaultdict
import time
import re
from datetime import timedelta, datetime
from flask import Flask
from threading import Thread
import os

# ================== KEEP ALIVE ==================
app = Flask('')

@app.route('/')
def home():
    return "Bot aktif"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ================== BOT AYARLARI ==================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="a!", intents=intents, help_command=None)

OWNER_ROLE = 1529961136081076294
MUTE_ROLE  = 1529960144312471602
BAN_ROLE   = 1529959924900167870

SPAM_COUNT = 5
SPAM_SECONDS = 7
MUTE_SURESI = 300

user_messages = defaultdict(list)
uyarilar = defaultdict(list)

REKLAM_KELIMELERI = [
    "discord.gg", "discord.com/invite", "dc.gg", "davet", "sunucumuza",
    "katıl", "ücretsiz nitro", "nitro veriyorum", "nitro dağıtıyorum",
    "hesap sat", "hesap al", "ucuz nitro", "boost sat", "boost al",
    "reklam", "dm atın", "dm gel", "dm'den yazın", "özelden yazın",
    "sunucuya gel", "sunucuma gel", "davet linki", "invite", "nitro free",
    "bedava nitro", "ücretsiz boost", "hesap veriyorum", "çark", "çekiliş"
]

LOG_KANAL_ID = 1530901600032522320
HOSGELDIN_KANAL_ID = 1529984361112539288

def is_owner():
    async def predicate(ctx):
        return any(role.id == OWNER_ROLE for role in ctx.author.roles)
    return commands.check(predicate)

def can_mute():
    async def predicate(ctx):
        return any(role.id in [OWNER_ROLE, MUTE_ROLE] for role in ctx.author.roles)
    return commands.check(predicate)

def can_ban():
    async def predicate(ctx):
        return any(role.id in [OWNER_ROLE, BAN_ROLE] for role in ctx.author.roles)
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Bot hazır → {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="a!yardim"
        )
    )

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    if any(role.id == OWNER_ROLE for role in message.author.roles):
        await bot.process_commands(message)
        return

    content = message.content.lower()
    user_id = message.author.id
    now = time.time()

    # sa cevabı
    if content in ["sa", "sea", "selam", "slm", "selamın aleyküm", "selamunaleykum"]:
        await message.channel.send(
            f"Aleyküm Selam safire hoş geldin yetkili olmak için nickine safir alarak ve kuralları okumayı unutma {message.author.mention}"
        )

    # Reklam kontrolü
    reklam = False
    if re.search(r"(discord\.gg|discord\.com/invite|dc\.gg|discordapp\.com/invite)", content):
        reklam = True
    for kelime in REKLAM_KELIMELERI:
        if kelime in content:
            reklam = True
            break
    if message.embeds:
        for embed in message.embeds:
            text = f"{embed.title or ''} {embed.description or ''}".lower()
            if any(k in text for k in REKLAM_KELIMELERI):
                reklam = True

    if reklam:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} **sg orospu çocuğu** reklam yasak, ban yedin.")
            await message.author.ban(reason="Reklam - Otomatik")
        except:
            pass
        return

    # Spam kontrolü
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < SPAM_SECONDS]
    user_messages[user_id].append(now)

    if len(user_messages[user_id]) >= SPAM_COUNT:
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} **oc spam yapma** amk")
            await message.author.timeout(discord.utils.utcnow() + timedelta(seconds=MUTE_SURESI), reason="Spam")
            user_messages[user_id].clear()
        except:
            pass
        return

    await bot.process_commands(message)

# ================== DETAYLI LOGLAR ==================
@bot.event
async def on_member_join(member):
    # DM at
    try:
        await member.send(
            "Aleyküm Selam safire hoş geldin yetkili olmak için nickine safir alarak ve kuralları okumayı unutma"
        )
    except:
        pass

    # Log kanalı
    log_kanal = bot.get_channel(LOG_KANAL_ID)
    if log_kanal:
        hesap = member.created_at.strftime("%d.%m.%Y %H:%M")
        await log_kanal.send(
            f"**🟢 GİRİŞ**\n"
            f"Kullanıcı: {member.mention} (`{member}`)\n"
            f"ID: `{member.id}`\n"
            f"Hesap Açılış: `{hesap}`\n"
            f"Üye Sayısı: **{member.guild.member_count}**"
        )

    # Hoş geldin kanalı
    hosgeldin = bot.get_channel(HOSGELDIN_KANAL_ID)
    if hosgeldin:
        await hosgeldin.send(
            f"Aleyküm Selam safire hoş geldin yetkili olmak için nickine safir alarak ve kuralları okumayı unutma {member.mention}"
        )

@bot.event
async def on_member_remove(member):
    log_kanal = bot.get_channel(LOG_KANAL_ID)
    if log_kanal:
        await log_kanal.send(
            f"**🔴 ÇIKIŞ**\n"
            f"Kullanıcı: {member.mention} (`{member}`)\n"
            f"ID: `{member.id}`\n"
            f"Üye Sayısı: **{member.guild.member_count}**"
        )

@bot.event
async def on_member_ban(guild, user):
    log_kanal = bot.get_channel(LOG_KANAL_ID)
    if log_kanal:
        sebep = "Bilinmiyor"
        yetkili = "Bilinmiyor"
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    sebep = entry.reason or "Sebep belirtilmemiş"
                    yetkili = f"{entry.user.mention} (`{entry.user}`)"
                    break
        except:
            pass

        await log_kanal.send(
            f"**⛔ BAN**\n"
            f"Kullanıcı: {user.mention} (`{user}`)\n"
            f"Yetkili: {yetkili}\n"
            f"Sebep: `{sebep}`\n"
            f"Üye Sayısı: **{guild.member_count}**"
        )

@bot.event
async def on_member_unban(guild, user):
    log_kanal = bot.get_channel(LOG_KANAL_ID)
    if log_kanal:
        yetkili = "Bilinmiyor"
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    yetkili = f"{entry.user.mention} (`{entry.user}`)"
                    break
        except:
            pass

        await log_kanal.send(
            f"**🔓 UNBAN**\n"
            f"Kullanıcı: {user.mention} (`{user}`)\n"
            f"Yetkili: {yetkili}"
        )

@bot.event
async def on_member_update(before, after):
    log_kanal = bot.get_channel(LOG_KANAL_ID)
    if not log_kanal:
        return

    # İsim değişikliği
    if before.display_name != after.display_name:
        await log_kanal.send(
            f"**📝 İSİM DEĞİŞTİ**\n"
            f"Kullanıcı: {after.mention} (`{after}`)\n"
            f"Eski: `{before.display_name}`\n"
            f"Yeni: `{after.display_name}`"
        )

    # Rol değişikliği
    if before.roles != after.roles:
        eklenen = [r for r in after.roles if r not in before.roles]
        cikarilan = [r for r in before.roles if r not in after.roles]

        yetkili = "Bilinmiyor"
        try:
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    yetkili = f"{entry.user.mention} (`{entry.user}`)"
                    break
        except:
            pass

        if eklenen:
            roller = ", ".join([f"{r.mention} (`{r.name}`)" for r in eklenen])
            await log_kanal.send(
                f"**➕ ROL VERİLDİ**\n"
                f"Kullanıcı: {after.mention} (`{after}`)\n"
                f"Rol: {roller}\n"
                f"Yetkili: {yetkili}"
            )

        if cikarilan:
            roller = ", ".join([f"{r.mention} (`{r.name}`)" for r in cikarilan])
            await log_kanal.send(
                f"**➖ ROL ALINDI**\n"
                f"Kullanıcı: {after.mention} (`{after}`)\n"
                f"Rol: {roller}\n"
                f"Yetkili: {yetkili}"
            )

# ================== KOMUTLAR ==================

@bot.command()
@can_mute()
async def mute(ctx, member: discord.Member, sure: int = 5, *, sebep="Sebep belirtilmedi"):
    if any(role.id == OWNER_ROLE for role in member.roles):
        return await ctx.send("Owner'ı mute atamazsın.")
    try:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=sure), reason=sebep)
        embed = discord.Embed(color=discord.Color.orange())
        embed.description = f"**{member.mention}** `{sure}` dakika mutelendi.\nSebep: {sebep}"
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Mute atılamadı: {e}")

@bot.command()
@can_mute()
async def unmute(ctx, member: discord.Member):
    try:
        await member.timeout(None)
        await ctx.send(f"**{member.mention}** unmute edildi.")
    except Exception as e:
        await ctx.send(f"Unmute yapılamadı: {e}")

@bot.command()
@can_ban()
async def ban(ctx, member: discord.Member, *, sebep="Sebep belirtilmedi"):
    if any(role.id == OWNER_ROLE for role in member.roles):
        return await ctx.send("Owner'ı banlayamazsın.")
    try:
        await member.ban(reason=sebep)
        embed = discord.Embed(color=discord.Color.red())
        embed.description = f"**{member}** banlandı.\nSebep: {sebep}"
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Ban atılamadı: {e}")

@bot.command()
@can_ban()
async def unban(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"**{user}** unban edildi.")
    except Exception as e:
        await ctx.send(f"Unban yapılamadı: {e}")

@bot.command()
@is_owner()
async def kick(ctx, member: discord.Member, *, sebep="Sebep belirtilmedi"):
    try:
        await member.kick(reason=sebep)
        await ctx.send(f"**{member}** kicklendi.\nSebep: {sebep}")
    except Exception as e:
        await ctx.send(f"Kick atılamadı: {e}")

@bot.command()
@can_mute()
async def uyarı(ctx, member: discord.Member, *, sebep="Sebep belirtilmedi"):
    uyarilar[member.id].append(sebep)
    sayi = len(uyarilar[member.id])
    await ctx.send(f"**{member.mention}** uyarıldı. (`{sayi}. uyarı`)\nSebep: {sebep}")
    if sayi >= 3:
        try:
            await member.timeout(discord.utils.utcnow() + timedelta(hours=1), reason="3 uyarı")
            await ctx.send(f"**{member.mention}** 3 uyarı aldığı için 1 saat mutelendi.")
        except:
            pass

@bot.command()
@can_mute()
async def uyarılar(ctx, member: discord.Member):
    liste = uyarilar.get(member.id, [])
    if not liste:
        return await ctx.send(f"**{member}** için hiç uyarı yok.")
    text = "\n".join([f"**{i+1}.** {s}" for i, s in enumerate(liste)])
    embed = discord.Embed(title=f"{member} Uyarıları", description=text, color=discord.Color.orange())
    await ctx.send(embed=embed)

@bot.command()
@is_owner()
async def uyarısil(ctx, member: discord.Member):
    uyarilar[member.id].clear()
    await ctx.send(f"**{member}** uyarıları silindi.")

@bot.command()
@is_owner()
async def sil(ctx, miktar: int = 10):
    await ctx.channel.purge(limit=miktar + 1)
    msg = await ctx.send(f"`{miktar}` mesaj silindi.")
    await msg.delete(delay=3)

@bot.command()
@is_owner()
async def nuke(ctx):
    try:
        if not ctx.guild.me.guild_permissions.manage_channels:
            return await ctx.send("Botun **Kanalları Yönet** izni yok!")

        channel = ctx.channel
        position = channel.position
        category = channel.category

        new_channel = await channel.clone(reason=f"Nuke - {ctx.author}")
        await new_channel.edit(position=position, category=category)
        await channel.delete(reason=f"Nuke - {ctx.author}")

        await new_channel.send(
            content=f"**{ctx.author.mention}** kanalı nukeledi 💥",
            embed=discord.Embed().set_image(url="https://media.tenor.com/yNqQ6QqX8Q8AAAAC/explosion-nuke.gif")
        )

    except Exception as e:
        await ctx.send(f"Nuke atılamadı: `{e}`")

@bot.command()
@is_owner()
async def lock(ctx):
    try:
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        overwrite.add_reactions = False
        overwrite.create_public_threads = False
        overwrite.send_messages_in_threads = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(description="🔒 Kanal kilitlendi.", color=discord.Color.red())
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Kilit atılamadı: {e}")

@bot.command()
@is_owner()
async def unlock(ctx):
    try:
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        overwrite.add_reactions = True
        overwrite.create_public_threads = True
        overwrite.send_messages_in_threads = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(description="🔓 Kanal kilidi açıldı.", color=discord.Color.green())
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Kilit açılamadı: {e}")

@bot.command()
@is_owner()
async def slowmode(ctx, saniye: int = 0):
    await ctx.channel.edit(slowmode_delay=saniye)
    if saniye == 0:
        await ctx.send("Slowmode kapatıldı.")
    else:
        await ctx.send(f"Slowmode `{saniye}` saniye olarak ayarlandı.")

@bot.command()
@is_owner()
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send("Önce bir ses kanalına gir.")
    channel = ctx.author.voice.channel
    try:
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect(reconnect=True, self_deaf=True)
        await ctx.send(f"**{channel.name}** kanalına girdim, AFK kalıyorum.")
    except Exception as e:
        await ctx.send(f"Sese giremedim: {e}")

@bot.command()
@is_owner()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Sesten çıktım.")
    else:
        await ctx.send("Zaten seste değilim.")

@bot.command()
@is_owner()
async def say(ctx, *, mesaj):
    await ctx.message.delete()
    await ctx.send(mesaj)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member} Avatarı", color=discord.Color.blurple())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def sunucu(ctx):
    guild = ctx.guild
    owner = guild.owner

    text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
    voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
    categories = len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])

    embed = discord.Embed(
        title=f"{guild.name} | Sunucu Bilgileri",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="👑 Sunucu Sahibi", value=f"{owner.mention}", inline=False)
    embed.add_field(name="🆔 Sunucu ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="📅 Oluşturulma Tarihi", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="📁 Kanal Sayısı", value=f"**{len(guild.channels)}**\n{text_channels} Yazı | {voice_channels} Ses | {categories} Kategori", inline=False)
    embed.add_field(name="👥 Üye Sayısı", value=f"**{guild.member_count}**", inline=True)
    embed.add_field(name="🎭 Rol Sayısı", value=f"**{len(guild.roles)}**", inline=True)
    embed.add_field(name="💎 Boost Sayısı", value=f"**{guild.premium_subscription_count}**", inline=True)

    embed.set_footer(text=f"bugün saat {datetime.now().strftime('%H:%M')}")
    await ctx.send(embed=embed)

@bot.command(name="yardim")
async def yardim(ctx):
    embed = discord.Embed(
        title="Komut Menüsü",
        description="Prefix: **a!**",
        color=discord.Color.red()
    )
    embed.add_field(
        name="Mute Yetkisi",
        value="`a!mute @kişi 10 sebep`\n`a!unmute @kişi`\n`a!uyarı @kişi sebep`\n`a!uyarılar @kişi`",
        inline=False
    )
    embed.add_field(
        name="Ban Yetkisi",
        value="`a!ban @kişi sebep`\n`a!unban 123456789`",
        inline=False
    )
    embed.add_field(
        name="Owner Yetkisi",
        value="`a!kick @kişi sebep`\n`a!sil 30`\n`a!nuke`\n`a!lock` / `a!unlock`\n`a!slowmode 5`\n`a!join` / `a!leave`\n`a!say mesaj`\n`a!uyarısil @kişi`",
        inline=False
    )
    embed.add_field(
        name="Herkes",
        value="`a!sunucu`\n`a!avatar @kişi`\n`a!yardim`",
        inline=False
    )
    embed.set_footer(text="Reklam yapanlar otomatik ban yer.")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("Bu komutu kullanmaya yetkin yok.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Eksik argüman girdin. `a!yardim` yaz.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Kullanıcı bulunamadı.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Yanlış argüman girdin.")
    else:
        print(f"Hata: {error}")

# ================== BAŞLAT ==================
keep_alive()
bot.run(os.getenv("TOKEN"))
