# -*- coding: utf-8 -*-
"""
CasinoForge - Fun & Utility Module
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. /meme
    @app_commands.command(name="meme", description="Fetch a random gaming or coding meme.")
    async def meme(self, interaction: discord.Interaction):
        # We defer the response because API calls can occasionally take a few seconds
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://meme-api.com/gimme/ProgrammerHumor+gaming") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(title=data['title'], url=data['postLink'], color=discord.Color.random())
                        embed.set_image(url=data['url'])
                        embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']}")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("❌ Meme API is currently down. Try again later!")
        except Exception:
            await interaction.followup.send("❌ Failed to fetch a meme. The internet must be acting up.")

    # 2. /avatar
    @app_commands.command(name="avatar", description="Display a high-res version of a user's profile picture.")
    @app_commands.describe(user="The user whose avatar you want to see")
    async def avatar(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        embed = discord.Embed(title=f"{target.display_name}'s Avatar", color=discord.Color.blurple())
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # 3. /roast
    @app_commands.command(name="roast", description="Deliver a lighthearted roast to a friend.")
    @app_commands.describe(user="The target of the roast")
    async def roast(self, interaction: discord.Interaction, user: discord.User):
        roasts = [
            f"I'd challenge {user.mention} to a battle of wits, but I see they are unarmed.",
            f"{user.mention} is the reason the developer put an `/eco-wipe` command in this bot.",
            f"If {user.mention} was a video game, they'd be rated 'E' for Everyone is disappointed.",
            f"I was going to make a joke about {user.mention}'s gaming skills, but their stats are already a joke.",
            f"{user.mention}'s code is so messy, even ChatGPT refused to debug it."
        ]
        await interaction.response.send_message(random.choice(roasts))

    # 4. /8ball
    @app_commands.command(name="8ball", description="Consult the mystical 8-ball for a definitive answer.")
    @app_commands.describe(question="The question you want to ask")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.",
            "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
            "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
            "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        
        embed = discord.Embed(title="🎱 The Magic 8-Ball", color=discord.Color.dark_purple())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(responses), inline=False)
        await interaction.response.send_message(embed=embed)

    # 5. /predict-wealth
    @app_commands.command(name="predict-wealth", description="Let the bot predict how rich a user will be in 5 years.")
    @app_commands.describe(user="The user to predict for")
    async def predict_wealth(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        predictions = [
            "Billionaire CEO of a mega-corporation. 🏢💰",
            "Living in a cardboard box behind a Wendy's. 📦🍔",
            "Still begging the bot for spare coins every 10 minutes. 🥺🪙",
            "Lost everything in a terrible 50/50 all-in coinflip. 🪙💀",
            "Living comfortably on a private island after hitting the lottery jackpot. 🏝️💎"
        ]
        await interaction.response.send_message(f"🔮 **Crystal Ball:** In 5 years, {target.mention} will be: \n*{random.choice(predictions)}*")

    # 6. /roll
    @app_commands.command(name="roll", description="Roll a custom polyhedral die (e.g., a D20).")
    @app_commands.describe(sides="Number of sides on the die")
    async def roll(self, interaction: discord.Interaction, sides: int = 6):
        if sides < 2:
            return await interaction.response.send_message("❌ A die needs at least 2 sides!", ephemeral=True)
        if sides > 1000000:
            return await interaction.response.send_message("❌ That's too many sides. The die rolled into the 4th dimension.", ephemeral=True)
            
        result = random.randint(1, sides)
        await interaction.response.send_message(f"🎲 {interaction.user.mention} rolled a **D{sides}** and got a **{result}**!")

    # 7. /flex
    @app_commands.command(name="flex", description="Spend 500 coins just to broadcast a flashy wealth message to the channel.")
    async def flex(self, interaction: discord.Interaction):
        flex_cost = 500
        
        async with self.bot.db_pool.acquire() as conn:
            # We don't bother creating the user here, if they don't exist, they definitely don't have 500 coins.
            wallet = await conn.fetchval("SELECT wallet FROM users WHERE user_id = $1", str(interaction.user.id))
            
            if not wallet or wallet < flex_cost:
                return await interaction.response.send_message(f"❌ You are too poor to flex! You need at least **{flex_cost}** coins.", ephemeral=True)
                
            await conn.execute("UPDATE users SET wallet = wallet - $1 WHERE user_id = $2", flex_cost, str(interaction.user.id))
            
        embed = discord.Embed(
            title="💎 ULTIMATE FLEX 💎", 
            description=f"**{interaction.user.display_name}** just burned **{flex_cost}** coins solely to remind everyone in this channel that they are rich.",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    # 8. /quote
    @app_commands.command(name="quote", description="Drop an inspiring or wildly out-of-context quote.")
    async def quote(self, interaction: discord.Interaction):
        quotes = [
            "\"I have come here to chew bubblegum and write code... and I'm all out of bubblegum.\" - Unknown Developer",
            "\"It's not a bug, it's an undocumented feature.\" - Anonymous",
            "\"Talk is cheap. Show me the code.\" - Linus Torvalds",
            "\"You miss 100% of the shots you don't take.\" - Wayne Gretzky - Michael Scott",
            "\"99% of gamblers quit right before they hit the jackpot.\" - CasinoForge Admin"
        ]
        await interaction.response.send_message(f"📜 {random.choice(quotes)}")

    # 9. /hug
    @app_commands.command(name="hug", description="Send a wholesome action message to another user.")
    @app_commands.describe(user="The user you want to hug")
    async def hug(self, interaction: discord.Interaction, user: discord.User):
        if user.id == interaction.user.id:
            await interaction.response.send_message(f"🫂 {interaction.user.mention} gave themselves a tight hug. Self-love is important!")
        else:
            await interaction.response.send_message(f"🫂 **{interaction.user.display_name}** wraps their arms around **{user.display_name}** for a big hug!")

    # 10. /coin-flip-pure
    @app_commands.command(name="coin-flip-pure", description="A standard coin flip that has absolutely no money tied to it.")
    async def coin_flip_pure(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(f"🪙 The coin flipped in the air and landed on... **{result}**!")

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
