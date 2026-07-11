# -*- coding: utf-8 -*-
"""
CasinoForge - Core Engine
"""

import discord
from discord import app_commands  # 👈 Added this missing import!
from discord.ext import commands
import asyncpg
import os
import asyncio
import logging

# 1. Advanced Logging Setup
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CasinoForge')

class CasinoForge(commands.Bot):
    def __init__(self, db_pool: asyncpg.Pool, creator_ids: list[int]):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None 
        )
        
        self.db_pool = db_pool
        self.creator_ids = creator_ids
        self.maintenance_mode = False

    async def setup_hook(self):
        # Attach the error handler directly to the tree inside the setup hook safely
        self.tree.on_error = self.on_app_command_error

        initial_cogs = ["cogs.gambling", "cogs.staff", "cogs.creator", "cogs.fun", "cogs.action", "cogs.beg"]
        
        for cog in initial_cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Successfully loaded module: {cog}")
            except Exception as e:
                logger.warning(f"Skipped loading {cog} (File not built yet): {e}")

        logger.info("Syncing slash commands globally... (This takes a moment)")
        await self.tree.sync()
        logger.info("Global slash commands synced successfully!")

    async def on_ready(self):
        logger.info(f"Bot Online! Logged in as {self.user.name} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="High Stakes | /help"))

    # 👈 This is the clean, built-in way to catch cooldown spam perfectly!
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            seconds = error.retry_after
            if seconds >= 60:
                time_left = f"{int(seconds // 60)}m {int(seconds % 60)}s"
            else:
                time_left = f"{seconds:.1f}s"
                
            try:
                await interaction.response.send_message(
                    f"⏳ **Slow down!** You can use this command again in **{time_left}**.",
                    ephemeral=True
                )
            except Exception:
                pass
            return

        logger.error(f"Unhandled slash command error: {error}")


async def main():
    TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
    CREATOR_IDS = [1075340640243691520, 1307955870713380884] # Add more IDs here

    if not TOKEN or not DATABASE_URL:
        logger.error("FATAL BOOT ERROR: BOT_TOKEN or DATABASE_URL missing from environment variables!")
        return

    logger.info("Initializing Supabase database connection pool...")
    try:
        pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=30)
        logger.info("Connected to Supabase PostgreSQL flawlessly.")
    except Exception as e:
        logger.error(f"FATAL DATABASE ERROR: Could not connect to Supabase: {e}")
        return

    async with pool:
        bot = CasinoForge(db_pool=pool, creator_ids=CREATOR_IDS)
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot manually shut down by the developer.")
