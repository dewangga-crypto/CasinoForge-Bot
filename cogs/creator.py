# -*- coding: utf-8 -*-
"""
CasinoForge - Creator Cog
Developer-only commands for bot management
"""

import discord
from discord.ext import commands
import app_commands
import logging

logger = logging.getLogger('CasinoForge.Creator')

class CreatorOnly(app_commands.check):
    """Check if user is the bot creator."""
    async def __call__(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != interaction.client.creator_id:
            await interaction.response.send_message(
                "❌ This command is restricted to the bot creator.",
                ephemeral=True
            )
            return False
        return True

class Creator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dev-shutdown", description="[Creator] Shutdown the bot.")
    @CreatorOnly()
    async def dev_shutdown(self, interaction: discord.Interaction):
        """Developer: Shutdown bot."""
        await interaction.response.send_message(
            "🛑 Bot shutting down...",
            ephemeral=True
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

    @app_commands.command(name="dev-echo", description="[Creator] Echo a message.")
    @CreatorOnly()
    @app_commands.describe(message="Message to echo")
    async def dev_echo(self, interaction: discord.Interaction, message: str):
        """Developer: Echo test command."""
        await interaction.response.send_message(
            f"🔊 Echo: {message}",
            ephemeral=True
        )

    @app_commands.command(name="dev-ping", description="[Creator] Ping the bot.")
    @CreatorOnly()
    async def dev_ping(self, interaction: discord.Interaction):
        """Developer: Ping test."""
        await interaction.response.send_message(
            f"🏓 Pong! Latency: {self.bot.latency * 1000:.2f}ms",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Creator(bot))
    logger.info("Creator cog loaded")
