# -*- coding: utf-8 -*-
"""
CasinoForge - Creator Cog
Developer-only commands for bot management
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import sys
import os

logger = logging.getLogger('CasinoForge.Creator')

def CreatorOnly():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id not in interaction.client.creator_ids:
            await interaction.response.send_message(
                "❌ This command is restricted to the bot creator.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

class Creator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="maintenance", description="[Creator] Toggles global maintenance mode.")
    @CreatorOnly()
    async def maintenance(self, interaction: discord.Interaction):
        """Toggle maintenance mode."""
        self.bot.maintenance_mode = not self.bot.maintenance_mode
        status = "ENABLED 🛠️" if self.bot.maintenance_mode else "DISABLED ✅"
        
        await interaction.response.send_message(
            f"🚧 **Maintenance Mode** is now **{status}**.\n"
            f"{'Regular users can no longer play casino games.' if self.bot.maintenance_mode else 'Regular users can now play games again.'}",
            ephemeral=True
        )
        logger.info(f"Maintenance mode toggled to: {self.bot.maintenance_mode}")

    @app_commands.command(name="dev-logs", description="[Creator] Fetch the latest bot logs.")
    @CreatorOnly()
    async def dev_logs(self, interaction: discord.Interaction):
        """Fetch logs."""
        try:
            with open("bot.log", "r") as f:
                logs = f.readlines()[-20:]
            log_text = "".join(logs)
            await interaction.response.send_message(f"📜 **Latest Logs:**\n```\n{log_text}\n```", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Could not read log file.", ephemeral=True)

    @app_commands.command(name="dev-leave", description="[Creator] Force the bot to leave a guild.")
    @CreatorOnly()
    @app_commands.describe(guild_id="ID of the guild to leave")
    async def dev_leave(self, interaction: discord.Interaction, guild_id: str):
        """Force leave guild."""
        guild = self.bot.get_guild(int(guild_id))
        if guild:
            await guild.leave()
            await interaction.response.send_message(f"👋 Left guild: **{guild.name}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Guild not found.", ephemeral=True)

    @app_commands.command(name="dev-reload", description="[Creator] Hot-reload a cog module.")
    @CreatorOnly()
    @app_commands.describe(module="Module name: gambling, action, staff, creator, or fun")
    async def dev_reload(self, interaction: discord.Interaction, module: str):
        """Developer: Reload a cog."""
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.reload_extension(f"cogs.{module.lower()}")
            await interaction.followup.send(
                f"🔄 Module `cogs.{module.lower()}` successfully reloaded!"
            )
            logger.info(f"Reloaded cog: cogs.{module.lower()}")
        except Exception as e:
            await interaction.followup.send(
                f"❌ **Reload Failed:**\n```py\n{e}\n```"
            )
            logger.error(f"Failed to reload cog: {e}")

    @app_commands.command(name="dev-status", description="[Creator] Check bot status and stats.")
    @CreatorOnly()
    async def dev_status(self, interaction: discord.Interaction):
        """Developer: Check bot status."""
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=discord.Color.green()
        )
        embed.add_field(name="Bot Name", value=self.bot.user.name, inline=True)
        embed.add_field(name="Bot ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.2f}ms", inline=True)
        embed.add_field(name="Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Maintenance", value="ON 🛠️" if self.bot.maintenance_mode else "OFF ✅", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dev-shutdown", description="[Creator] Shutdown the bot.")
    @CreatorOnly()
    async def dev_shutdown(self, interaction: discord.Interaction):
        """Developer: Shutdown bot."""
        await interaction.response.send_message(
            "🛑 Bot shutting down...",
        )
        logger.warning("Bot shutdown initiated by creator")
        await self.bot.close()

    @app_commands.command(name="dev-sync", description="[Creator] Sync slash commands globally.")
    @CreatorOnly()
    async def dev_sync(self, interaction: discord.Interaction):
        """Developer: Sync slash commands."""
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(
                f"✅ Synced **{len(synced)}** command(s) globally."
            )
            logger.info(f"Synced {len(synced)} commands")
        except Exception as e:
            await interaction.followup.send(
                f"❌ Sync failed: {e}"
            )
            logger.error(f"Failed to sync commands: {e}")

    @app_commands.command(name="dev-eval", description="[Creator] Evaluate Python code.")
    @CreatorOnly()
    @app_commands.describe(code="Python code to evaluate")
    async def dev_eval(self, interaction: discord.Interaction, code: str):
        """Developer: Eval code."""
        await interaction.response.defer(ephemeral=True)
        try:
            result = eval(code)
            await interaction.followup.send(f"✅ **Result:**\n```py\n{result}\n```")
        except Exception as e:
            await interaction.followup.send(f"❌ **Error:**\n```py\n{e}\n```")

    @app_commands.command(name="dev-sql", description="[Creator] Execute a raw SQL query.")
    @CreatorOnly()
    @app_commands.describe(query="SQL query to execute")
    async def dev_sql(self, interaction: discord.Interaction, query: str):
        """Developer: Run SQL."""
        await interaction.response.defer(ephemeral=True)
        try:
            async with self.bot.db_pool.acquire() as conn:
                if query.strip().lower().startswith("select"):
                    rows = await conn.fetch(query)
                    if not rows:
                        await interaction.followup.send("✅ Query executed successfully. No results returned.")
                        return
                    
                    header = " | ".join(rows[0].keys())
                    lines = [header, "-" * len(header)]
                    for row in rows[:10]:
                        lines.append(" | ".join(str(v) for v in row.values()))
                    
                    result_text = "\n".join(lines)
                    if len(rows) > 10:
                        result_text += f"\n... and {len(rows) - 10} more rows."
                        
                    await interaction.followup.send(f"📊 **Query Results:**\n```\n{result_text}\n```")
                else:
                    status = await conn.execute(query)
                    await interaction.followup.send(f"✅ Query executed successfully: `{status}`")
        except Exception as e:
            await interaction.followup.send(f"❌ **Database Error:**\n```py\n{e}\n```")

    @app_commands.command(name="dev-guilds", description="[Creator] List all guilds the bot is in.")
    @CreatorOnly()
    async def dev_guilds(self, interaction: discord.Interaction):
        """Developer: List guilds."""
        guilds = self.bot.guilds
        guild_list = "\n".join([f"• {g.name} ({g.id}) - {g.member_count} members" for g in guilds[:20]])
        
        embed = discord.Embed(
            title=f"🏰 Connected Guilds ({len(guilds)})",
            description=guild_list if guild_list else "No guilds found.",
            color=discord.Color.blue()
        )
        if len(guilds) > 20:
            embed.set_footer(text=f"Showing first 20 out of {len(guilds)} guilds.")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="global-announcement-setup", 
        description="[Admin] Set the channel where global announcements will be received."
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(channel="The channel where announcements should go")
    async def global_announcement_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO server_settings (guild_id, announcement_channel_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET announcement_channel_id = EXCLUDED.announcement_channel_id
                """,
                str(interaction.guild_id),
                str(channel.id)
            )
            
        await interaction.followup.send(
            f"✅ Successfully set {channel.mention} as this server's global announcement channel!",
            ephemeral=True
        )

    @app_commands.command(
        name="global-say", 
        description="[Creator] Broadcast an announcement to all configured server channels."
    )
    @CreatorOnly()  
    @app_commands.describe(message="The message or announcement content to broadcast everywhere")
    async def global_say(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)
        
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT announcement_channel_id FROM server_settings")
            
        if not rows:
            await interaction.followup.send(
                "❌ No servers have configured a global announcement channel using `/global-announcement-setup` yet.",
                ephemeral=True
            )
            return

        success_count = 0
        fail_count = 0

        for row in rows:
            channel_id = int(row['announcement_channel_id'])
            channel = self.bot.get_channel(channel_id)
            
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception:
                    fail_count += 1
                    continue
                    
            try:
                await channel.send(message)
                success_count += 1
            except Exception:
                fail_count += 1

        await interaction.followup.send(
            f"📢 **Global Announcement Dispatched!**\n"
            f"✅ Sent successfully to **{success_count}** channel(s).\n"
            f"❌ Failed/Skipped **{fail_count}** channel(s).",
            ephemeral=True
        )

    @app_commands.command(name="dev-shell", description="[Creator] Execute a shell command.")
    @CreatorOnly()
    @app_commands.describe(command="Shell command to run")
    async def dev_shell(self, interaction: discord.Interaction, command: str):
        """Developer: Run shell command."""
        await interaction.response.defer(ephemeral=True)
        try:
            import subprocess
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=10).decode()
            if len(result) > 1900:
                result = result[:1900] + "\n... (truncated)"
            await interaction.followup.send(f"💻 **Shell Output:**\n```\n{result}\n```")
        except Exception as e:
            await interaction.followup.send(f"❌ **Error:**\n```\n{e}\n```")

    @app_commands.command(name="dev-reboot", description="[Creator] Reboot the bot process.")
    @CreatorOnly()
    async def dev_reboot(self, interaction: discord.Interaction):
        """Developer: Reboot bot."""
        await interaction.response.send_message("🔄 Rebooting...")
        logger.warning("Bot reboot initiated by creator")
        os.execv(sys.executable, ['python3'] + sys.argv)

async def setup(bot: commands.Bot):
    await bot.add_cog(Creator(bot))
    logger.info("Creator cog loaded")
