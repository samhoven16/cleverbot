import ssl
import certifi
import discord
from discord.ext import commands, tasks
import anthropic
import os
import json
import aiohttp
from dotenv import load_dotenv
from datetime import datetime, date
from collections import defaultdict
load_dotenv()

# Fix SSL certificates on macOS
ssl_context = ssl.create_default_context(cafile=certifi.where())

# --- Config ---
TOKEN = os.getenv("DISCORD_TOKEN")
CLAUDE_KEY = os.getenv("ANTHROPIC_API_KEY")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "your-email@example.com")
TOPGG_TOKEN = os.getenv("TOPGG_TOKEN", "")
BOT_ID = "1486859682311045271"
TOPGG_VOTE_URL = f"https://top.gg/bot/{BOT_ID}/vote"

# --- Free tier ---
FREE_DAILY_LIMIT = 3
VOTE_BONUS = 5  # extra questions for voting
usage_tracker = defaultdict(lambda: {"count": 0, "date": str(date.today())})
vote_bonus_tracker = defaultdict(int)  # user_id -> bonus questions remaining

# --- Files ---
PREMIUM_SERVERS_FILE = "premium_servers.json"
PAYMENTS_FILE = "payments.json"
VOTERS_FILE = "voters.json"

# --- Helpers ---
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

def load_voters():
    if os.path.exists(VOTERS_FILE):
        with open(VOTERS_FILE) as f:
            return json.load(f)
    return {}

def save_voter(user_id):
    voters = load_voters()
    voters[str(user_id)] = str(datetime.now())
    with open(VOTERS_FILE, "w") as f:
        json.dump(voters, f, indent=2)

premium_servers = load_premium()

# --- Bot setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
claude = anthropic.Anthropic(api_key=CLAUDE_KEY)

# --- On ready ---
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is live in {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Game("!ask | AI Assistant | !vote"))
    daily_upsell.start()
    vote_reminder.start()
    post_stats.start()
    print("🚀 All automations started")

# --- New server: auto welcome ---
@bot.event
async def on_guild_join(guild):
    print(f"Joined: {guild.name} ({guild.id})")
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send(
                f"👋 **CleverBot has arrived!**\n\n"
                f"I'm an AI assistant powered by Claude AI.\n\n"
                f"**Try me now:** `!ask what can you do?`\n\n"
                f"🆓 **Free:** {FREE_DAILY_LIMIT} questions/day\n"
                f"⭐ **Premium:** Unlimited for $9.99/month → `{OWNER_EMAIL}`\n"
                f"🗳️ **Vote for free bonus questions:** {TOPGG_VOTE_URL}"
            )
            break

# --- Auto: post server count to top.gg every 30 min (boosts ranking) ---
@tasks.loop(minutes=30)
async def post_stats():
    if not TOPGG_TOKEN:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"https://top.gg/api/bots/{BOT_ID}/stats",
                json={"server_count": len(bot.guilds)},
                headers={"Authorization": TOPGG_TOKEN}
            )
            print(f"📊 Posted stats: {len(bot.guilds)} servers")
    except Exception as e:
        print(f"Stats post error: {e}")

@post_stats.before_loop
async def before_stats():
    await bot.wait_until_ready()

# --- Auto: daily upsell to free servers ---
@tasks.loop(hours=24)
async def daily_upsell():
    for guild in bot.guilds:
        if guild.id not in premium_servers:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(
                        f"💡 **CleverBot Daily Tip**\n"
                        f"Use `!ask` to get instant AI answers on anything!\n\n"
                        f"🗳️ Vote for free bonus questions: {TOPGG_VOTE_URL}\n"
                        f"⭐ Go unlimited with Premium: `{OWNER_EMAIL}`"
                    )
                    break

@daily_upsell.before_loop
async def before_upsell():
    await bot.wait_until_ready()

# --- Auto: vote reminder every 12 hours ---
@tasks.loop(hours=12)
async def vote_reminder():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"🗳️ **Vote for CleverBot on top.gg — it's free!**\n"
                    f"Voting takes 5 seconds and gives you **{VOTE_BONUS} bonus questions**!\n"
                    f"👉 {TOPGG_VOTE_URL}"
                )
                break

@vote_reminder.before_loop
async def before_vote():
    await bot.wait_until_ready()

# --- Commands ---
@bot.command(name="ask")
async def ask(ctx, *, question: str):
    """Ask the AI anything."""
    server_id = ctx.guild.id
    user_id = ctx.author.id

    if server_id not in premium_servers:
        tracker = usage_tracker[server_id]
        if tracker["date"] != str(date.today()):
            tracker["count"] = 0
            tracker["date"] = str(date.today())

        # Use vote bonus first
        if vote_bonus_tracker[user_id] > 0:
            vote_bonus_tracker[user_id] -= 1
        elif tracker["count"] >= FREE_DAILY_LIMIT:
            await ctx.send(
                f"⚠️ **Daily limit reached** ({FREE_DAILY_LIMIT} questions/day on free plan).\n"
                f"🗳️ **Vote for {VOTE_BONUS} free bonus questions:** {TOPGG_VOTE_URL}\n"
                f"⭐ **Or go unlimited:** `{OWNER_EMAIL}`"
            )
            return
        else:
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
                bonus = vote_bonus_tracker[user_id]
                footer = f"\n\n*Free — {left} questions left today{f' + {bonus} vote bonus' if bonus > 0 else ''}. Vote for more: {TOPGG_VOTE_URL}*"
            await ctx.send(f"{answer}{footer}")
        except Exception as e:
            await ctx.send("❌ Something went wrong. Try again.")
            print(f"Error: {e}")

@bot.command(name="vote")
async def vote(ctx):
    """Get bonus questions by voting on top.gg."""
    await ctx.send(
        f"🗳️ **Vote for CleverBot — completely free!**\n\n"
        f"👉 {TOPGG_VOTE_URL}\n\n"
        f"After voting you get **{VOTE_BONUS} bonus questions** instantly!\n"
        f"You can vote every 12 hours."
    )

@bot.command(name="voted")
async def voted(ctx):
    """Claim your vote bonus (use after voting on top.gg)."""
    user_id = ctx.author.id
    voters = load_voters()
    if str(user_id) in voters:
        vote_bonus_tracker[user_id] += VOTE_BONUS
        await ctx.send(f"✅ Thanks for voting! You got **{VOTE_BONUS} bonus questions**!")
        save_voter(user_id)
    else:
        await ctx.send(
            f"❌ Vote not detected yet.\n"
            f"1. Vote here: {TOPGG_VOTE_URL}\n"
            f"2. Then type `!voted` again."
        )

@bot.command(name="status")
async def status(ctx):
    """Check plan and usage."""
    server_id = ctx.guild.id
    user_id = ctx.author.id
    if server_id in premium_servers:
        await ctx.send(f"⭐ **Premium Plan** — Unlimited AI questions!")
    else:
        tracker = usage_tracker[server_id]
        if tracker["date"] != str(date.today()):
            tracker["count"] = 0
        left = FREE_DAILY_LIMIT - tracker["count"]
        bonus = vote_bonus_tracker[user_id]
        await ctx.send(
            f"📊 **Free Plan**\n"
            f"Questions left today: {left}/{FREE_DAILY_LIMIT}\n"
            f"Vote bonus: {bonus} questions\n\n"
            f"🗳️ Vote for more: {TOPGG_VOTE_URL}\n"
            f"⭐ Go unlimited: `{OWNER_EMAIL}`"
        )

@bot.command(name="upgrade")
async def upgrade(ctx):
    """Show upgrade info."""
    await ctx.send(
        f"⭐ **Upgrade to Premium**\n\n"
        f"✅ Unlimited AI questions\n"
        f"✅ No daily limits ever\n"
        f"✅ Priority support\n\n"
        f"💰 **$9.99/month per server**\n"
        f"📧 Pay via PayPal: `{OWNER_EMAIL}`\n"
        f"✅ Activated within 24 hours!"
    )

# --- Owner commands ---
@bot.command(name="activate")
@commands.is_owner()
async def activate(ctx, server_id: int):
    guild = bot.get_guild(server_id)
    name = guild.name if guild else "Unknown"
    premium_servers.add(server_id)
    save_premium(premium_servers)
    log_payment(server_id, name, 9.99)
    await ctx.send(f"✅ `{name}` ({server_id}) is now Premium. Payment logged.")

@bot.command(name="deactivate")
@commands.is_owner()
async def deactivate(ctx, server_id: int):
    premium_servers.discard(server_id)
    save_premium(premium_servers)
    await ctx.send(f"✅ Server `{server_id}` removed from Premium.")

@bot.command(name="earnings")
@commands.is_owner()
async def earnings(ctx):
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
    lines = "\n".join([f"• {g.name} — ID: `{g.id}` — {'⭐ Premium' if g.id in premium_servers else 'Free'}" for g in bot.guilds])
    await ctx.send(f"**Servers ({len(bot.guilds)}):**\n{lines}")

bot.run(TOKEN)
