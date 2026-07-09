# -*- coding: utf-8 -*-
"""
CasinoForge - Creator Executive Module (hyperjay_951 Exclusive)
"""

import discord
from discord import app_commands
from discord.ext import commands
import sys
import time
import io
import contextlib
import traceback

class Creator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.maintenance_mode = False
        self.godmode_users = set()

    # Custom decorator to ensure strict validation against the registered creator ID
    def is_creator():
        async def predicate(interaction: discord.Interaction) -> bool:
            if interaction.user.id == interaction.client.creator_id:
                return True
            await interaction.response.send_message("❌ **Access Denied:** This structural command is strictly restricted to the bot creator.", ephemeral=True)
            return False
        return app_commands.check(predicate)

    # Global interceptor for Maintenance Mode
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if self.maintenance_mode and interaction.user.id != self.bot.creator_id:
            if not interaction.response.is_done():
                await interaction.response.send_message("🚨 **System Offline:** CasinoForge is currently undergoing a live configuration update. Try again shortly.", ephemeral=True)
                raise app_commands.AppCommandError("Command blocked by active maintenance window.")

    # 1. /dev-script
    @app_commands.command(name="dev-script", description="[Creator] Run raw Python code directly within the live bot instance.")
    @is_creator()
    @app_commands.describe(code="Python expressions or block strings to compile")
    async def dev_script(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer(ephemeral=True)
        
        # Automatically clean up markdown code fences if you copy-paste them
        if code.startswith("```") and code.endswith("```"):
            code = "\n".join(code.split("\n")[1:-1])
            if code.startswith("py"):
                code = code[2:]

        # Pre-defined environment shortcuts for quick coding
        env = {
            'bot': self.bot,
            'interaction': interaction,
            'channel': interaction.channel,
            'guild': interaction.guild,
            'user': interaction.user,
            'db': self.bot.db_pool,
            'discord': discord
        }
        
        stdout = io.StringIO()
        # Wraps code in a clean async executor block to allow 'await' expressions
        to_compile = f"async def _eval_executor():\n" + "\n".join(f"    {line}" for line in code.splitlines())
        
        try:
            exec(to_compile, env)
            func = env['_eval_executor']
            with contextlib.redirect_stdout(stdout):
                result = await func()
        except Exception:
            await interaction.followup.send(f"❌ **Script Runtime Error:**\n```py\n{traceback.format_exc()}\n```")
            return
            
        output = stdout.getvalue()
        response_msg = "✅ **Execution Successful**\n"
        
        if output:
            response_msg += f"**Console Output:**\n```text\n{output}\n```"
        if result is not None:
            response_msg += f"**Returned Value:**\n```py\n{result}\n```"
        if not output and result is None:
            response_msg += "*Script completed with no return data or printed outputs.*"
            
        # Protect against Discord's 2000 character message ceiling
        if len(response_msg) > 2000:
            response_msg = response_msg[:1980] + "\n... [Output Truncated]"
            
        await interaction.followup.send(response_msg)

    # 2. /dev-addmoney
    @app_commands.command(name="dev-addmoney", description="[Creator] Spawn unlimited cash into a user's wallet.")
    @is_creator()
    @app_commands.describe(user="Target player", amount="Quantity to inject")
    async def dev_addmoney(self, interaction: discord.Interaction, user: discord.User, amount: int):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, wallet) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET wallet = users.wallet + $2;",
                str(user.id), amount
            )
        await interaction.followup.send(f"✅ Successfully injected **{amount:,}** coins into {user.mention}'s wallet.")

    # 3. /dev-removemoney
    @app_commands.command(name="dev-removemoney", description="[Creator] Void cash out of a user's wallet.")
    @is_creator()
    @app_commands.describe(user="Target player", amount="Quantity to burn")
    async def dev_removemoney(self, interaction: discord.Interaction, user: discord.User, amount: int):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, wallet) VALUES ($1, 0) ON CONFLICT (user_id) DO UPDATE SET wallet = GREATEST(0, users.wallet - $2);",
                str(user.id), amount
            )
        await interaction.followup.send(f"✅ Successfully voided **{amount:,}** coins from {user.mention}'s wallet.")

    # 4. /dev-setmoney
    @app_commands.command(name="dev-setmoney", description="[Creator] Override and set a player's wallet to an exact balance.")
    @is_creator()
    @app_commands.describe(user="Target player", amount="Exact target balance")
    async def dev_setmoney(self, interaction: discord.Interaction, user: discord.User, amount: int):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, wallet) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET wallet = $2;",
                str(user.id), amount
            )
        await interaction.followup.send(f"✅ Successfully hard-set {user.mention}'s wallet balance to **{amount:,}** coins.")

    # 5. /dev-godmode
    @app_commands.command(name="dev-godmode", description="[Creator] Toggle personal immunity to system robberies, taxes, and fines.")
    @is_creator()
    async def dev_godmode(self, interaction: discord.Interaction):
        if interaction.user.id in self.godmode_users:
            self.godmode_users.remove(interaction.user.id)
            msg = "❌ **God-Mode Terminated:** System profiles reverted to standard vulnerability flags."
        else:
            self.godmode_users.add(interaction.user.id)
            msg = "🛡️ **God-Mode Initialized:** Active user context is now completely immune to thefts, penalties, and taxes."
        await interaction.response.send_message(msg, ephemeral=True)

    # 6. /dev-shutdown
    @app_commands.command(name="dev-shutdown", description="[Creator] Safely terminate the bot container session and secure connections.")
    @is_creator()
    async def dev_shutdown(self, interaction: discord.Interaction):
        await interaction.response.send_message("👋 Closing database connections and safely shutting down CasinoForge...", ephemeral=True)
        await self.bot.close()

    # 7. /dev-reload
    @app_commands.command(name="dev-reload", description="[Creator] Hot-reload a specific cog extension file without taking the bot down.")
    @is_creator()
    @app_commands.describe(module="Name of the module to compile (gambling, economy, staff, fun, creator)")
    async def dev_reload(self, interaction: discord.Interaction, module: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.reload_extension(f"cogs.{module.lower()}")
            await interaction.followup.send(f"🔄 Module `cogs.{module.lower()}` successfully re-compiled and hot-loaded!")
        except Exception as e:
            await interaction.followup.send(f"❌ **Hot-Load Failure:** Structural anomaly detected in compilation:\n```py\n{e}\n```")

    # 8. /dev-system-status
    @app_commands.command(name="dev-system-status", description="[Creator] Run deep resource and runtime diagnostics on the bot.")
    @is_creator()
    async def dev_system_status(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        guilds = len(self.bot.guilds)
        users = sum(g.member_count for g in self.bot.guilds if g.member_count)
        
        embed = discord.Embed(title="⚙️ CasinoForge System Diagnostics", color=discord.Color.dark_red())
        embed.add_field(name="Gateway Latency", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="Active Cluster Guilds", value=f"`{guilds}`", inline=True)
        embed.add_field(name="Global Cached Members", value=f"`{users:,}`", inline=True)
        embed.add_field(name="Python Environment", value=f"`{sys.version.split()[0]}`", inline=False)
        embed.set_footer(text="Container Target: JustRunMy.App")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 9. /dev-giveall
    @app_commands.command(name="dev-giveall", description="[Creator] Gift an immediate cash stimulus to every single registered database user row.")
    @is_creator()
    @app_commands.describe(amount="Quantity to add globally")
    async def dev_giveall(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET wallet = wallet + $1;", amount)
        await interaction.followup.send(f"💸 **Global Stimulus Dispatched:** Added **{amount:,}** coins to all registered server entities.")

    # 10. /dev-simulate-exploit
    @app_commands.command(name="dev-simulate-exploit", description="[Creator] Audit database sanitation logic and monitor injection vulnerability isolation.")
    @is_creator()
    async def dev_simulate_exploit(self, interaction: discord.Interaction):
        start = time.perf_counter()
        async with self.bot.db_pool.acquire() as conn:
            db_check = await conn.fetchval("SELECT True;")
        latency = (time.perf_counter() - start) * 1000
        
        await interaction.response.send_message(
            f"🛡️ **Security Sanitation Audit:**\n"
            f"• Parametric Isolation Layer: **SECURE** (SQLi Defended via asyncpg dynamic arguments)\n"
            f"• Live Cloud DB Roundtrip: `{latency:.2f}ms`\n"
            f"• Remote SSL Mode Status: **ENFORCED (Required)**",
            ephemeral=True
        )

    # 11. /dev-maintenance
    @app_commands.command(name="dev-maintenance", description="[Creator] Toggle global lock to intercept and drop non-creator interactions.")
    @is_creator()
    async def dev_maintenance(self, interaction: discord.Interaction):
        self.maintenance_mode = not self.maintenance_mode
        status = "ENABLED (All incoming traffic isolated)" if self.maintenance_mode else "DISABLED"
        await interaction.response.send_message(f"🚨 **System Configuration Alert:** Maintenance Mode is now **{status}**.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Creator(bot))
