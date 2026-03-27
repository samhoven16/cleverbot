import ssl
import certifi
import discord
from discord.ext import commands, tasks
import anthropic
import os
import json
import aiohttp
from dotenv import load_dotenv
from datetime import datetime, date, timedelta
from collections import defaultdict
load_dotenv()

ssl_context = ssl.create_default_context(cafile=certifi.where())

# --- Config ---
TOKEN = os.getenv("DISCORD_TOKEN")
CLAUDE_KEY = os.getenv("ANTHROPIC_API_KEY")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "your-email@example.com")
TOPGG_TOKEN = os.getenv("TOPGG_TOKEN", "")
BOT_ID = "1486859682311045271"
TOPGG_VOTE_URL = f"https://top.gg/bot/{BOT_ID}/vote"

FREE_DAILY_LIMIT = 3
VOTE_BONUS = 5

# --- Files ---
PREMIUM_SERVERS_FILE = "premium_servers.json"
PAYMENTS_FILE = "payments.json"
USAGE_FILE = "usage.json"
VOTERS_FILE = "voters.json"

# --- Persistent usage tracking (survives restarts) ---
def load_usage():
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE) as f:
            return json.load(f)
    return {}

def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

def get_usage(server_id):
    data = load_usage()
    key = str(server_id)
    today = str(date.today())
    if key not in data or data[key]["date"] != today:
        data[key] = {"count": 0, "date": today}
        save_usage(data)
    return data, key

def increment_usage(server_id):
    data, key = get_usage(server_id)
    data[key]["count"] += 1
    save_usage(data)

# --- Premium ---
def load_premium():
    if os.path.exists(PREMIUM_SERVERS_FILE):
        with open(PREMIUM_SERVERS_FILE) as f:
            return set(json.load(f))
    return set()

def save_premium(servers):
    with open(PREMIUM_SERVERS_FILE, "w") as f:
        json.dump(list(servers), f)

# --- Payments ---
def load_payments():
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE) as f:
            return json.load(f)
    return []

def log_payment(server_id, server_name, amount):
    payments = load_payments()
    payments.append({
        "date": str(datetime.now()),
        "server_id": server_id,
        "server_name": server_name,
        "amount": amount
    })
    with open(PAYMENTS_FILE, "w") as f:
        json.dump(payments, f, indent=2)

# --- Voters (prevent double-claiming) ---
def load_voters():
    if os.path.exists(VOTERS_FILE):
        with open(VOTERS_FILE) as f:
            return json.load(f)
    return {}

def has_claimed_vote_today(user_id):
    voters = load_voters()
    key = str(user_id)
    if key not in voters:
        return False
    last = datetime.fromisoformat(voters[key])
    return datetime.now() - last < timedelta(hours=12)

def record_vote_claim(user_id):
    voters = load_voters()
    voters[str(user_id)] = str(datetime.now())
    with open(VOTERS_FILE, "w") as f:
        json.dump(voters, f, indent=2)

# --- Vote bonus (persistent) ---
def get_vote_bonus(user_id):
    voters = load_voters()
    return voters.get(f"bonus_{user_id}", 0)

def set_vote_bonus(user_id, amount):
    voters = load_voters()
    voters[f"bonus_{user_id}"] = amount
    with open(VOTERS_FILE, "w") as f:
        json.dump(voters, f, indent=2)

premium_servers = load_premium()

# --- Bot setup ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
claude = anthropic.Anthropic(api_key=CLAUDE_KEY)

# --- BUG FIX: check if tasks already running before starting ---
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is live in {len(bot.guilds)} servers")
    await bot.change_presence(activity=discord.Game("!ask | AI Assistant | !vote"))
    if not daily_upsell.is_running():
        daily_upsell.start()
    if not vote_reminder.is_running():
        vote_reminder.start()
    if not post_stats.is_running():
        post_stats.start()
    print("🚀 All automations started")

@bot.event
async def on_guild_join(guild):
    print(f"Joined: {guild.name} ({guild.id})")
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send(
                f"👋 **CleverBot has arrived!**\n\n"
                f"I'm an AI assistant powered by Claude AI.\n\n"
                f"**Try me:** `!ask what can you do?`\n"
                f"🆓 **Free:** {FREE_DAILY_LIMIT} questions/day\n"
                f"⭐ **Premium:** Unlimited for $9.99/month → `{OWNER_EMAIL}`\n"
                f"🗳️ **Vote for bonus questions:** {TOPGG_VOTE_URL}"
            )
            break

# --- Auto: post server count to top.gg (boosts ranking) ---
@tasks.loop(hours=1)
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
    except Exception as e:
        print(f"Stats post error: {e}")

@post_stats.before_loop
async def before_stats():
    await bot.wait_until_ready()

# --- BUG FIX: upsell weekly not daily (daily gets bots kicked) ---
@tasks.loop(hours=168)
async def daily_upsell():
    for guild in bot.guilds:
        if guild.id not in premium_servers:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(
                        f"💡 **CleverBot Weekly Tip**\n"
                        f"Use `!ask` to get instant AI answers!\n\n"
                        f"🗳️ Vote free for bonus questions: {TOPGG_VOTE_URL}\n"
                        f"⭐ Go unlimited with Premium: `{OWNER_EMAIL}`"
                    )
                    break

@daily_upsell.before_loop
async def before_upsell():
    await bot.wait_until_ready()

# --- BUG FIX: vote reminder weekly not every 12h (was extremely spammy) ---
@tasks.loop(hours=168)
async def vote_reminder():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"🗳️ **Vote for CleverBot — free & takes 5 seconds!**\n"
                    f"Get **{VOTE_BONUS} bonus questions** just for voting!\n"
                    f"👉 {TOPGG_VOTE_URL}"
                )
                break

@vote_reminder.before_loop
async def before_vote():
    await bot.wait_until_ready()

# --- Commands ---
@bot.command(name="ask")
async def ask(ctx, *, question: str):
    server_id = ctx.guild.id
    user_id = ctx.author.id

    if server_id not in premium_servers:
        data, key = get_usage(server_id)
        count = data[key]["count"]
        bonus = get_vote_bonus(user_id)

        if bonus > 0:
            set_vote_bonus(user_id, bonus - 1)
        elif count >= FREE_DAILY_LIMIT:
            await ctx.send(
                f"⚠️ **Daily limit reached** ({FREE_DAILY_LIMIT}/day on free plan).\n"
                f"🗳️ **Vote for {VOTE_BONUS} free bonus questions:** {TOPGG_VOTE_URL}\n"
                f"⭐ **Go unlimited:** `{OWNER_EMAIL}`"
            )
            return
        else:
            increment_usage(server_id)
            data, key = get_usage(server_id)
            count = data[key]["count"]

    async with ctx.typing():
        try:
            response = claude.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": question}]
            )
            answer = response.content[0].text
            if server_id in premium_servers:
                footer = "\n\n*⭐ Premium*"
            else:
                data, key = get_usage(server_id)
                left = FREE_DAILY_LIMIT - data[key]["count"]
                bonus = get_vote_bonus(user_id)
                footer = f"\n\n*Free — {left} left today{f' + {bonus} bonus' if bonus > 0 else ''}. More: {TOPGG_VOTE_URL}*"
            await ctx.send(f"{answer}{footer}")
        except Exception as e:
            await ctx.send("❌ Something went wrong. Try again.")
            print(f"Error: {e}")

@bot.command(name="vote")
async def vote(ctx):
    await ctx.send(
        f"🗳️ **Vote for CleverBot — completely free!**\n\n"
        f"👉 {TOPGG_VOTE_URL}\n\n"
        f"After voting type `!voted` to claim **{VOTE_BONUS} bonus questions**!\n"
        f"You can vote every 12 hours."
    )

# --- BUG FIX: voted now checks top.gg API + prevents double-claiming ---
@bot.command(name="voted")
async def voted(ctx):
    user_id = ctx.author.id

    if has_claimed_vote_today(user_id):
        await ctx.send("⏳ You already claimed your vote bonus in the last 12 hours. Vote again after 12 hours!")
        return

    if not TOPGG_TOKEN:
        await ctx.send("⚠️ Vote verification not set up yet. Contact the bot owner.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                f"https://top.gg/api/bots/{BOT_ID}/check?userId={user_id}",
                headers={"Authorization": TOPGG_TOKEN}
            )
            data = await resp.json()

        if data.get("voted") == 1:
            current = get_vote_bonus(user_id)
            set_vote_bonus(user_id, current + VOTE_BONUS)
            record_vote_claim(user_id)
            await ctx.send(f"✅ Vote confirmed! You got **{VOTE_BONUS} bonus questions**. Thanks for supporting CleverBot!")
        else:
            await ctx.send(
                f"❌ No vote detected yet.\n"
                f"1. Vote here: {TOPGG_VOTE_URL}\n"
                f"2. Wait a few seconds\n"
                f"3. Type `!voted` again"
            )
    except Exception as e:
        await ctx.send("❌ Could not verify vote. Try again in a moment.")
        print(f"Vote check error: {e}")

@bot.command(name="status")
async def status(ctx):
    server_id = ctx.guild.id
    user_id = ctx.author.id
    if server_id in premium_servers:
        await ctx.send("⭐ **Premium Plan** — Unlimited AI questions!")
    else:
        data, key = get_usage(server_id)
        left = FREE_DAILY_LIMIT - data[key]["count"]
        bonus = get_vote_bonus(user_id)
        await ctx.send(
            f"📊 **Free Plan**\n"
            f"Questions left today: {left}/{FREE_DAILY_LIMIT}\n"
            f"Vote bonus: {bonus} questions\n\n"
            f"🗳️ Vote for more: {TOPGG_VOTE_URL}\n"
            f"⭐ Go unlimited: `{OWNER_EMAIL}`"
        )

@bot.command(name="upgrade")
async def upgrade(ctx):
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
