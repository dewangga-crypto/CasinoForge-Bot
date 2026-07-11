# -*- coding: utf-8 -*-
"""
CasinoForge - Beg Command Module
"""
import discord
from discord.ext import commands
from discord import app_commands
import random
import logging

logger = logging.getLogger('CasinoForge.Beg')

class Beg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="beg", description="Beg for some spare change from the high rollers.")
    async def beg(self, interaction: discord.Interaction):
        # 1. Roll the outcome (20% failure rate)
        if random.random() < 0.20:
            rejections = [
                "Get a job, bum!",
                "I only give to charity, and you look like trouble.",
                "Look somewhere else, I'm fresh out of cash.",
                "The high rollers laugh and walk past you."
            ]
            await interaction.response.send_message(f"❌ {random.choice(rejections)}", ephemeral=True)
            return

        earnings = random.randint(50, 250)
        user_id_str = str(interaction.user.id)

        try:
            # 2. Safe Database Transaction via asyncpg pool
            async with self.bot.db_pool.acquire() as conn:
                async with conn.transaction():
                    # Check if user exists
                    user = await conn.fetchrow("SELECT wallet FROM users WHERE user_id = $1", user_id_str)
                    
                    if user:
                        # User exists, add coins to wallet
                        await conn.execute(
                            "UPDATE users SET wallet = wallet + $1 WHERE user_id = $2", 
                            earnings, user_id_str
                        )
                    else:
                        # User doesn't exist yet, register them safely
                        await conn.execute(
                            "INSERT INTO users (user_id, wallet, bank) VALUES ($1, $2, 0)", 
                            user_id_str, earnings
                        )

            # 3. Success Output
            success_messages = [
                f"A generous high roller tossed you **{earnings:,}** coins!",
                f"You found **{earnings:,}** coins left behind on a blackjack table!",
                f"Someone felt bad for you and handed you **{earnings:,}** coins."
            ]
            await interaction.response.send_message(f"🪙 {random.choice(success_messages)}")

        except Exception as e:
            logger.error(f"Database error in beg command: {e}")
            await interaction.response.send_message("⚠️ An error occurred processing your transaction.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Beg(bot))
    logger.info("Beg cog loaded successfully")
