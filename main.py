# -*- coding: utf-8 -*-
"""
CasinoForge - Core Engine
"""

import discord
from discord.ext import commands
import asyncpg
import os
import asyncio
import logging

# 1. Advanced Logging Setup
# This ensures all errors/connections are visible in your JustRunMy.App console
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('CasinoForge')

class CasinoForge(commands.Bot):
    def __init__(self, db_pool: asyncpg.Pool, creator_id: int):
        # Intents allow the bot to read message states and sync data
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!", # Fallback dev prefix, standard users will use / commands
            intents=intents,
            help_command=None # We will write a dynamic custom help slash command later
        )
        
        # Attach the database pool and your developer ID directly to the bot instance 
        # so every single command file can access them instantly.
        self.db_pool = db_pool
        self.creator_id = creator_id

    async def setup_hook(self):
        # We will build these 5 files one by one next.
        initial_cogs = ["cogs.gambling", "cogs.staff", "cogs.creator", "cogs.fun", "cogs.action"]
        
        # We use a try-except block here. This guarantees the bot boots perfectly today 
        # even though we haven't written the files in the cogs folder yet.
        for cog in initial_cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Successfully loaded module: {cog}")
            except Exception as e:
                logger.warning(f"Skipped loading {cog} (File not built yet): {e}")

        # Registers all slash commands globally to Discord's servers
        logger.info("Syncing slash commands globally... (This takes a moment)")
        await self.tree.sync()
        logger.info("Global slash commands synced successfully!")

    async def on_ready(self):
        logger.info(f"Bot Online! Logged in as {self.user.name} (ID: {self.user.id})")
        # Sets the Discord status to "Playing High Stakes | /help"
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="High Stakes | /help"))

async def main():
    # 2. Container Environment Variables
    # The bot securely reads your credentials from JustRunMy.App without hardcoding them
    TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # We can hardcode this safely since User IDs are strictly public info, not secure tokens.
    CREATOR_ID =  1075340640243691520

    if not TOKEN or not DATABASE_URL:
        logger.error("FATAL BOOT ERROR: BOT_TOKEN or DATABASE_URL missing from environment variables!")
        return

    logger.info("Initializing Supabase database connection pool...")
    try:
        # command_timeout=30 prevents database queries from freezing your bot if the cloud lags
        pool = await asyncpg.create_pool(DATABASE_URL, command_timeout=30)
        logger.info("Connected to Supabase PostgreSQL flawlessly.")
    except Exception as e:
        logger.error(f"FATAL DATABASE ERROR: Could not connect to Supabase: {e}")
        return

    # 3. Boot the Bot
    async with pool:
        bot = CasinoForge(db_pool=pool, creator_id=CREATOR_ID)
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot manually shut down by the developer.")
