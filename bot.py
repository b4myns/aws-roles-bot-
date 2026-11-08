import discord
from discord.ext import commands
import pandas as pd
import asyncio
import os
# ==============================================================================
# CONFIGURATION
# ==============================================================================


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Set the DISCORD_TOKEN environment variable")
GUILD_ID = 1563527148558622780  

# Direct match to the exact role names shown on your Discord server
ROLES_TO_ASSIGN = ["devlopment", "technical", "cc", "logistic"]

# ==============================================================================
# BOT INITIALIZATION & INTENTS
# ==============================================================================
intents = discord.Intents.default()
intents.members = True          # Enabled in Developer Portal -> Bot -> Server Members Intent
intents.message_content = True  # Allows bot to read !sync_sheet and !test_sync

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"Logged in as: {bot.user.name} (ID: {bot.user.id})")
    print("Ready to assign roles.")
    print("=" * 50)

# ==============================================================================
# COMMAND 1: TEST COMMAND (!test_sync)
# ==============================================================================
@bot.command(name="test_sync")
@commands.has_permissions(administrator=True)
async def test_sync(ctx):
    """Tests dual assignment specifically for test_members.csv"""
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        await ctx.send("❌ Error: Guild not found. Check GUILD_ID.")
        return

    # Cache roles
    cached_roles = {}
    for role_name in ROLES_TO_ASSIGN:
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
        if role:
            cached_roles[role_name] = role
        else:
            await ctx.send(f"⚠️ Warning: Role `{role_name}` not found in Server Settings!")

    try:
        df = pd.read_csv("test_members.csv")
    except FileNotFoundError:
        await ctx.send("❌ Error: `test_members.csv` not found.")
        return

    status_msg = await ctx.send("⏳ Running test sync for `Spiderrajel`...")
    assigned_count = 0

    for _, row in df.iterrows():
        raw_username = str(row.get("username", "")).strip().lower()
        dept = str(row.get("department", "")).strip().lower()

        target_role = cached_roles.get(dept)
        if not target_role:
            await ctx.send(f"⚠️ Role `{dept}` not found on server.")
            continue

        member = discord.utils.find(
            lambda m: m.name.lower() == raw_username 
                   or str(m.id) == raw_username 
                   or m.display_name.lower() == raw_username,
            guild.members
        )

        if member:
            if target_role not in member.roles:
                try:
                    await member.add_roles(target_role)
                    assigned_count += 1
                    await ctx.send(f"✅ Added `{target_role.name}` to {member.mention}")
                    await asyncio.sleep(0.5)
                except discord.Forbidden:
                    await ctx.send(f"❌ Permission error assigning `{target_role.name}`. Move bot role higher!")
            else:
                await ctx.send(f"ℹ️ {member.mention} already has `{target_role.name}`.")
        else:
            await ctx.send(f"❌ Could not find `{raw_username}` in the server.")

    await status_msg.edit(content=f"🎯 Test complete. Added {assigned_count} roles.")

# ==============================================================================
# COMMAND 2: FULL PRODUCTION COMMAND (!sync_sheet)
# ==============================================================================
@bot.command(name="sync_sheet")
@commands.has_permissions(administrator=True)
async def sync_sheet(ctx):
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        await ctx.send("❌ Error: Guild not found. Check that GUILD_ID is correct.")
        return

    # Cache roles from the server (case-insensitive lookup)
    cached_roles = {}
    for role_name in ROLES_TO_ASSIGN:
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), guild.roles)
        if not role:
            await ctx.send(f"⚠️ Warning: Role `{role_name}` not found in Server Settings!")
        else:
            cached_roles[role_name] = role

    # Read members-v2.csv
    try:
        df = pd.read_csv("members-v2.csv")
    except FileNotFoundError:
        await ctx.send("❌ Error: `members-v2.csv` not found in the bot directory.")
        return

    status_msg = await ctx.send("⏳ Starting role synchronization...")

    assigned_count = 0
    not_found = set()

    for _, row in df.iterrows():
        raw_username = str(row.get("username", "")).strip().lower()
        dept = str(row.get("department", "")).strip().lower()

        if not raw_username or dept not in cached_roles:
            continue

        target_role = cached_roles[dept]

        # Match member by username, user ID, or display name
        member = discord.utils.find(
            lambda m: m.name.lower() == raw_username
                   or str(m.id) == raw_username
                   or m.display_name.lower() == raw_username,
            guild.members
        )

        if member:
            if target_role not in member.roles:
                try:
                    await member.add_roles(target_role)
                    assigned_count += 1
                    print(f"[{assigned_count}] Added '{target_role.name}' to {member.name}")
                    await asyncio.sleep(0.5)  # Rate limit safety delay
                except discord.Forbidden:
                    print(f"❌ Permission error for {member.name}. Check role hierarchy!")
            else:
                print(f"ℹ️ {member.name} already has '{target_role.name}'.")
        else:
            not_found.add(raw_username)

    # Output report
    report = f"✅ **Role Sync Complete!**\n"
    report += f"• **Total roles assigned:** {assigned_count}\n"
    if not_found:
        report += f"• **Members not found in server ({len(not_found)}):**\n"
        report += "```\n" + ", ".join(list(not_found)) + "\n```"
    else:
        report += "• All members matched and updated successfully!"

    await status_msg.edit(content=report)

# ==============================================================================
# RUN THE BOT (MUST ALWAYS BE AT THE VERY BOTTOM)
# ==============================================================================
bot.run(TOKEN)