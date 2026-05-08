import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import json
import os
from dotenv import load_dotenv

#
#╔══════════════════════╗
#║      github.com      ║
#║    /toprakbuilds     ║
#╚══════════════════════╝
#
load_dotenv()  # .env dosyasına tokeninizi girin
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

STATUS_FILE = "bot_status.json"

def save_status(status_type, text):
    data = {
        "type": status_type,
        "text": text
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

async def load_status():
    if not os.path.exists(STATUS_FILE):
        return None, None
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("type"), data.get("text")

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı.")
    status_type, status_text = await load_status()
    valid_types = {
        "playing": discord.ActivityType.playing,
        "listening": discord.ActivityType.listening,
        "watching": discord.ActivityType.watching,
        "streaming": discord.ActivityType.streaming,
    }
    if status_type and status_text and status_type in valid_types:
        activity_type = valid_types[status_type]
        if activity_type == discord.ActivityType.streaming:
            await bot.change_presence(activity=discord.Streaming(name=status_text, url="https://www.twitch.tv/batujnax"))
        else:
            await bot.change_presence(activity=discord.Activity(type=activity_type, name=status_text))

@bot.command(name="müzik", aliases=["çal", "play"])
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        return await ctx.send("🎧 Önce bir ses kanalına katılmalısın!")

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    vc = ctx.voice_client

    async with ctx.typing():
        player = await YTDLSource.from_url(search, loop=bot.loop, stream=True)
        vc.play(player, after=lambda e: print(f"Player error: {e}") if e else None)
        vc.source.volume = 0.5

    await ctx.send(f"▶️ Şimdi çalınıyor: **{player.title}**")

@bot.command()
async def duraklat(ctx):
    vc = ctx.voice_client
    if not vc or not vc.is_playing():
        return await ctx.send("⏹️ Şu anda çalan müzik yok.")
    vc.pause()
    await ctx.send("⏸️ Müzik duraklatıldı.")

@bot.command()
async def devam(ctx):
    vc = ctx.voice_client
    if not vc or not vc.is_paused():
        return await ctx.send("⏹️ Şu anda duraklatılmış müzik yok.")
    vc.resume()
    await ctx.send("▶️ Müzik devam ediyor.")

@bot.command()
async def durdur(ctx):
    vc = ctx.voice_client
    if not vc:
        return await ctx.send("⏹️ Bot herhangi bir ses kanalında değil.")
    await vc.disconnect()
    await ctx.send("⏹️ Müzik durduruldu ve bot ses kanalından ayrıldı.")

@bot.command()
async def ses(ctx, volume: int):
    vc = ctx.voice_client
    if not vc or not (vc.is_playing() or vc.is_paused()):
        return await ctx.send("❌ Bot herhangi bir ses kanalında değil veya müzik çalmıyor.")
    if volume < 0 or volume > 100:
        return await ctx.send("❌ Ses seviyesi 0 ile 100 arasında olmalı.")
    try:
        vc.source.volume = volume / 100
        await ctx.send(f"🔊 Ses seviyesi {volume}% olarak ayarlandı.")
    except Exception as e:
        await ctx.send(f"❌ Ses seviyesi ayarlanırken hata oluştu: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def durum(ctx, tip: str, *, text: str):
    tip = tip.lower()
    valid_types = {
        "playing": discord.ActivityType.playing,
        "listening": discord.ActivityType.listening,
        "watching": discord.ActivityType.watching,
        "streaming": discord.ActivityType.streaming,
    }

    if tip not in valid_types:
        return await ctx.send(f"❌ Geçersiz tip! Şunlardan biri olmalı: {', '.join(valid_types.keys())}")

    activity_type = valid_types[tip]

    if activity_type == discord.ActivityType.streaming:
        await bot.change_presence(activity=discord.Streaming(name=text, url="https://www.twitch.tv/batujnax"))
    else:
        await bot.change_presence(activity=discord.Activity(type=activity_type, name=text))

    save_status(tip, text)  # Durumu dosyaya kaydet

    await ctx.send(f"✅ Durum `{tip}` olarak ayarlandı: {text}")

bot.run(TOKEN)

