import ssl
import certifi
import discord
from discord.ext import commands
from discord.ext import tasks
import anthropic
import os
import json
from dotenv import load_dotenv
from datetime import datetime, date
from collections import defaultdict
load_dotenv()

# Fix SSL certificates on macOS
ssl_context = ssl.create_default_context(cafile=certifi.where())

# --- Load config ---
TOKEN = os.getenv("DISCORD_TOKEN")
CLAUDE_KEY = os.getenv("ANTHROPIC_API_KEY")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "your-email@example.com")

# --- Free tier limits ---
FREE_DAILY_LIMIT = 5
usage_tracker = defaultdict(lambda: {"count": 0, "date": str(date.today())})

# --- Files ---
PREMIUM_SERVERS_FILE = "premium_servers.json"
PAYMENTS_FILE = "payments.json"

# --- Load/save helpers ---
def load_premium():
    if os.path.exists(PREMIUM_SERVERS_FILE):
        with open(PREMIUM_SERVERS_FILE) as f:
            return set(json.load(f))
    return set()

def save_premium(servers):
    with open(PREMIUM_SERVERS_FILE, "w") as f:
        json.dump(list(servers), f)

def load_payments():
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE) as f:
            return json.load(f)
    return []

def log_payment(server_id, server_name, amount, note=""):
    payments = load_payments()
    payments.append({
        "date": str(datetime.now()),
        "server_id": server_id,
        "server_name": server_name,
        "amount": amount,
        "note": note
    })
    with open(PAYMENTS_FILE, "w") as f:
        json.dump(payments, f, indent=2)

premium_servers = load_premium()

# --- Bot setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
claude = anthropic.Anthropic(api_key=CLAUDE_KEY)

# --- 24/7: Auto-restart on disconnect ---
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is live in {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Game("!ask | AI Assistant"))
    daily_upsell.start()
    print("📣 Daily upsell task started")

@bot.event
async def on_guild_join(guild):
    print(f"Joined: {guild.name} ({guild.id})")
    # Auto welcome + upsell when bot joins a new server
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send(
                f"👋 **CleverBot is here!**\n\n"
                f"I'm an AI assistant powered by Claude.\n\n"
                f"**Try me:** `!ask what can you do?`\n"
                f"**Free plan:** {FREE_DAILY_LIMIT} questions/day\n"
                f"**Premium:** Unlimited for $9.99/month → `{OWNER_EMAIL}`"
            )
            break

# --- Auto upsell: message free servers every 24 hours ---
@tasks.loop(hours=24)
async def daily_upsell():
    for guild in bot.guilds:
        if guild.id not in premium_servers:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(
                        f"💡 **CleverBot Tip:** Use `!ask` to get instant AI answers!\n"
                        f"⭐ Upgrade to **Premium** for unlimited questions: `{OWNER_EMAIL}`"
                    )
                    break

@daily_upsell.before_loop
async def before_upsell():
    await bot.wait_until_ready()

# --- Commands ---
@bot.command(name="ask")
async def ask(ctx, *, question: str):
    """Ask the AI anything."""
    server_id = ctx.guild.id

    if server_id not in premium_servers:
        tracker = usage_tracker[server_id]
        if tracker["date"] != str(date.today()):
            tracker["count"] = 0
            tracker["date"] = str(date.today())
        if tracker["count"] >= FREE_DAILY_LIMIT:
            await ctx.send(
                f"⚠️ **Daily limit reached** ({FREE_DAILY_LIMIT} questions/day on free plan).\n"
                f"⭐ Upgrade to **Premium** for unlimited: `{OWNER_EMAIL}`"
            )
            return
        tracker["count"] += 1

    async with ctx.typing():
        try:
            response = claude.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                messages=[{"role": "user", "content": question}]
            )
            answer = response.content[0].text
            if server_id in premium_servers:
                footer = "\n\n*⭐ Premium*"
            else:
                left = FREE_DAILY_LIMIT - usage_tracker[server_id]["count"]
                footer = f"\n\n*Free — {left} questions left today. Upgrade: `{OWNER_EMAIL}`*"
            await ctx.send(f"{answer}{footer}")
        except Exception as e:
            await ctx.send("❌ Something went wrong. Try again.")
            print(f"Error: {e}")

@bot.command(name="status")
async def status(ctx):
    """Check plan and usage."""
    server_id = ctx.guild.id
    if server_id in premium_servers:
        payments = [p for p in load_payments() if p["server_id"] == server_id]
        await ctx.send(f"⭐ **Premium Plan** — Unlimited AI questions!\nPayments logged: {len(payments)}")
    else:
        tracker = usage_tracker[server_id]
        if tracker["date"] != str(date.today()):
            tracker["count"] = 0
        left = FREE_DAILY_LIMIT - tracker["count"]
        await ctx.send(
            f"📊 **Free Plan** — {left}/{FREE_DAILY_LIMIT} questions left today\n"
            f"⭐ Go Premium for unlimited: `{OWNER_EMAIL}`"
        )

@bot.command(name="upgrade")
async def upgrade(ctx):
    """Show upgrade info."""
    await ctx.send(
        f"⭐ **Upgrade to Premium**\n\n"
        f"✅ Unlimited AI questions\n"
        f"✅ No daily limits\n"
        f"✅ Priority support\n\n"
        f"💰 **$9.99/month per server**\n"
        f"📧 Pay via PayPal: `{OWNER_EMAIL}`\n"
        f"Then you'll be activated within 24 hours!"
    )

# --- Owner commands ---
@bot.command(name="activate")
@commands.is_owner()
async def activate(ctx, server_id: int):
    """Activate premium for a server."""
    guild = bot.get_guild(server_id)
    name = guild.name if guild else "Unknown"
    premium_servers.add(server_id)
    save_premium(premium_servers)
    log_payment(server_id, name, 9.99)
    await ctx.send(f"✅ `{name}` ({server_id}) is now Premium. Payment logged.")

@bot.command(name="deactivate")
@commands.is_owner()
async def deactivate(ctx, server_id: int):
    """Remove premium from a server."""
    premium_servers.discard(server_id)
    save_premium(premium_servers)
    await ctx.send(f"✅ Server `{server_id}` removed from Premium.")

@bot.command(name="earnings")
@commands.is_owner()
async def earnings(ctx):
    """Show payment log and total earnings."""
    payments = load_payments()
    if not payments:
        await ctx.send("No payments logged yet.")
        return
    total = sum(p["amount"] for p in payments)
    lines = "\n".join([f"• {p['date'][:10]} — {p['server_name']} — ${p['amount']}" for p in payments[-10:]])
    await ctx.send(f"💰 **Total earned: ${total:.2f}**\n\nLast payments:\n{lines}")

@bot.command(name="servers")
@commands.is_owner()
async def servers(ctx):
    """List all servers the bot is in."""
    lines = "\n".join([f"• {g.name} — ID: `{g.id}` — {'⭐ Premium' if g.id in premium_servers else 'Free'}" for g in bot.guilds])
    await ctx.send(f"**Servers ({len(bot.guilds)}):**\n{lines}")

bot.run(TOKEN)
