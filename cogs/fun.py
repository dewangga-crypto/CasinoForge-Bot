# -*- coding: utf-8 -*-
"""
CasinoForge - Fun Cog
Non-economy entertainment and utility commands
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import logging

logger = logging.getLogger('CasinoForge.Fun')

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Get help with CasinoForge commands.")
    async def help(self, interaction: discord.Interaction):
        """Display help information."""
        embed = discord.Embed(
            title="🎰 CasinoForge - Command Help",
            description="A high-stakes Discord gambling economy bot",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🎲 **Gambling Games**",
            value="`/coinflip` `/slots` `/blackjack` `/roulette` `/crash` `/horserace` `/dice` `/lottery` `/gamble`",
            inline=False
        )
        
        embed.add_field(
            name="💰 **Economy**",
            value="`/balance` `/deposit` `/withdraw` `/work` `/give` `/request`",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ **Admin Commands** (requires admin)",
            value="`/eco-add` `/eco-remove` `/eco-freeze` `/eco-unfreeze` `/eco-wipe` `/eco-search` `/bank-limit` `/blacklist` `/unblacklist`",
            inline=False
        )
        
        embed.add_field(
            name="👨‍💻 **Developer Commands** (creator only)",
            value="`/maintenance` `/dev-reload` `/dev-status` `/dev-eval` `/dev-sql` `/dev-guilds` `/dev-sync` `/global-say` `/dev-shutdown`",
            inline=False
        )
        
        embed.add_field(
            name="🎉 **Fun**",
            value="`/quote` `/roll` `/flip`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quote", description="Get an inspiring quote.")
    async def quote(self, interaction: discord.Interaction):
        """Display a random quote."""
        quotes = [
            "\"I have come here to chew bubblegum and write code... and I'm all out of bubblegum.\" - Unknown Developer",
            "\"It's not a bug, it's an undocumented feature.\" - Anonymous",
            "\"Talk is cheap. Show me the code.\" - Linus Torvalds",
            "\"You miss 100% of the shots you don't take.\" - Wayne Gretzky - Michael Scott",
            "\"99% of gamblers quit right before they hit the jackpot.\" - CasinoForge",
            "\"The house always wins.\" - Every Casino",
            "\"I'm not superstitious, but I'm a little stitious.\" - Michael Scott",
            "\"May the odds be ever in your favor.\" - Hunger Games"
        ]
        await interaction.response.send_message(f"📜 {random.choice(quotes)}")

    @app_commands.command(name="roll", description="Roll a dice.")
    @app_commands.describe(sides="Number of sides (default: 6)")
    async def roll(self, interaction: discord.Interaction, sides: int = 6):
        """Roll a dice."""
        if sides < 2:
            await interaction.response.send_message("❌ Dice must have at least 2 sides.", ephemeral=True)
            return
        
        result = random.randint(1, sides)
        await interaction.response.send_message(
            f"🎲 You rolled a **{result}** out of **{sides}**!"
        )

    @app_commands.command(name="flip", description="Flip a coin.")
    async def flip(self, interaction: discord.Interaction):
        """Flip a coin."""
        result = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(
            f"🪙 The coin landed on **{result}**!"
        )

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a yes/no question.")
    @app_commands.describe(question="Your question")
    async def eightball(self, interaction: discord.Interaction, question: str):
        """Magic 8-ball response."""
        responses = [
            "Yes, definitely.",
            "No way.",
            "Maybe...",
            "Ask again later.",
            "It is certain.",
            "Don't count on it.",
            "Very doubtful.",
            "Outlook good.",
            "Signs point to yes.",
            "Without a doubt."
        ]
        
        response = random.choice(responses)
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            description=f"**Q:** {question}\n\n**A:** {response}",
            color=discord.Color.random()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="choose", description="Let the bot choose for you.")
    @app_commands.describe(options="Options separated by commas")
    async def choose(self, interaction: discord.Interaction, options: str):
        """Choose randomly from options."""
        choices = [opt.strip() for opt in options.split(",")]
        
        if len(choices) < 2:
            await interaction.response.send_message(
                "❌ Please provide at least 2 options separated by commas.",
                ephemeral=True
            )
            return
        
        choice = random.choice(choices)
        await interaction.response.send_message(
            f"🤔 I choose: **{choice}**"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
    logger.info("Fun cog loaded")
