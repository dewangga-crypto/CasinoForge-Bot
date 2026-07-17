# -*- coding: utf-8 -*-
"""
CasinoForge - Simple Investment Market Module
"""
import discord
from discord.ext import commands
from discord import app_commands
import random
import logging
from typing import Literal

logger = logging.getLogger('CasinoForge.Invest')

# hardcoding fictitious tickers and baseline ranges
STOCKS = {
    "FORGE": {"name": "CasinoForge Inc.", "min": 80, "max": 140},
    "CHIPS": {"name": "Blue Chip Holdings", "min": 40, "max": 75},
    "LUCK": {"name": "Lady Luck Ventures", "min": 10, "max": 45}
}

def get_live_price(ticker: str) -> int:
    """simulates a fluctuating price based on baseline bounds"""
    cfg = STOCKS[ticker]
    return random.randint(cfg["min"], cfg["max"])

class Invest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="market", description="Check current simulated stock market prices.")
    async def market(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📈 Forge Stock Exchange",
            color=discord.Color.blue()
        )
        
        for ticker, data in STOCKS.items():
            current_price = get_live_price(ticker)
            embed.add_field(
                name=f"{data['name']} (`${ticker}`)",
                value=f"Price: **{current_price}** coins\n*Fluctuates on every look*",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invest", description="Buy shares of a fake stock.")
    @app_commands.describe(ticker="The stock ticker to purchase", shares="Amount of shares to buy")
    async def invest(self, interaction: discord.Interaction, ticker: Literal["FORGE", "CHIPS", "LUCK"], shares: int):
        if shares <= 0:
            await interaction.response.send_message("❌ Amount of shares must be greater than zero.", ephemeral=True)
            return

        await interaction.response.defer()
        user_id_str = str(interaction.user.id)
        price_per_share = get_live_price(ticker)
        total_cost = price_per_share * shares

        try:
            async with self.bot.db_pool.acquire() as conn:
                async with conn.transaction():
                    # check if user can afford it
                    user = await conn.fetchrow("SELECT wallet FROM users WHERE user_id = $1", user_id_str)
                    if not user or user["wallet"] < total_cost:
                        await interaction.followup.send("❌ You don't have enough coins in your wallet for this.", ephemeral=True)
                        return

                    # take coins away
                    await conn.execute("UPDATE users SET wallet = wallet - $1 WHERE user_id = $2", total_cost, user_id_str)
                    
                    # save investment row
                    await conn.execute(
                        """
                        INSERT INTO investments (user_id, ticker, shares)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id, ticker)
                        DO UPDATE SET shares = investments.shares + EXCLUDED.shares
                        """,
                        user_id_str, ticker, shares
                    )

            await interaction.followup.send(
                f"📊 Bought **{shares:,}** share(s) of `${ticker}` at **{price_per_share}** each for a total of **{total_cost:,}** coins!"
            )
        except Exception as e:
            logger.error(f"Error executing buy query: {e}")
            await interaction.followup.send("⚠️ Failed to process trade transaction.", ephemeral=True)

    @app_commands.command(name="sell-stock", description="Sell your owned shares.")
    @app_commands.describe(ticker="The stock ticker to liquidate", shares="Amount of shares to sell")
    async def sell_stock(self, interaction: discord.Interaction, ticker: Literal["FORGE", "CHIPS", "LUCK"], shares: int):
        if shares <= 0:
            await interaction.response.send_message("❌ Amount of shares must be greater than zero.", ephemeral=True)
            return

        await interaction.response.defer()
        user_id_str = str(interaction.user.id)
        price_per_share = get_live_price(ticker)
        total_payout = price_per_share * shares

        try:
            async with self.bot.db_pool.acquire() as conn:
                async with conn.transaction():
                    # verify they actually own the shares
                    record = await conn.fetchrow(
                        "SELECT shares FROM investments WHERE user_id = $1 AND ticker = $2", 
                        user_id_str, ticker
                    )
                    if not record or record["shares"] < shares:
                        await interaction.followup.send("❌ You don't own enough shares to fulfill this trade.", ephemeral=True)
                        return

                    # remove or update shares row
                    if record["shares"] == shares:
                        await conn.execute("DELETE FROM investments WHERE user_id = $1 AND ticker = $2", user_id_str, ticker)
                    else:
                        await conn.execute(
                            "UPDATE investments SET shares = shares - $1 WHERE user_id = $2 AND ticker = $3",
                            shares, user_id_str, ticker
                        )

                    # pay out wallet cash
                    await conn.execute("UPDATE users SET wallet = wallet + $1 WHERE user_id = $2", total_payout, user_id_str)

            await interaction.followup.send(
                f"📉 Sold **{shares:,}** share(s) of `${ticker}` at **{price_per_share}** each. Received **{total_payout:,}** coins into your wallet!"
            )
        except Exception as e:
            logger.error(f"Error executing sell query: {e}")
            await interaction.followup.send("⚠️ Failed to process trade transaction.", ephemeral=True)

    @app_commands.command(name="portfolio", description="Check all assets you currently hold.")
    async def portfolio(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id_str = str(interaction.user.id)

        try:
            async with self.bot.db_pool.acquire() as conn:
                rows = await conn.fetch("SELECT ticker, shares FROM investments WHERE user_id = $1", user_id_str)

            if not rows:
                await interaction.followup.send("💼 Your portfolio is completely empty. Buy assets using `/buy`!")
                return

            embed = discord.Embed(
                title=f"💼 {interaction.user.name}'s Investment Portfolio",
                color=discord.Color.purple()
            )
            for row in rows:
                embed.add_field(
                    name=f"${row['ticker']}",
                    value=f"Shares Held: **{row['shares']:,}**",
                    inline=True
                )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error rendering portfolio embed: {e}")
            await interaction.followup.send("⚠️ Could not load your portfolio assets.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Invest(bot))
    logger.info("Investment market cog loaded")
