# -*- coding: utf-8 -*-
"""
CasinoForge - Gambling Cog
Contains all casino game commands
"""

import discord
from discord.ext import commands
import app_commands
import random
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('CasinoForge.Gambling')

class Gambling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.betting_cooldowns = {}  # Track recent bets

    async def ensure_user(self, user_id: int):
        """Ensure user exists in database with default values."""
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING;",
                str(user_id)
            )

    async def process_bet(self, interaction: discord.Interaction, bet: int) -> bool:
        """Deducts the bet and checks for restrictions. Returns True if successful."""
        if bet <= 0:
            await interaction.response.send_message("❌ Bet amount must be positive.", ephemeral=True)
            return False

        await self.ensure_user(interaction.user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT wallet, is_frozen, is_blacklisted FROM users WHERE user_id = $1",
                str(interaction.user.id)
            )
            
            if row is None:
                await interaction.response.send_message("❌ Account not found.", ephemeral=True)
                return False
            
            if row['is_frozen'] or row['is_blacklisted']:
                await interaction.response.send_message("❌ Your account is restricted.", ephemeral=True)
                return False
            
            if row['wallet'] < bet:
                await interaction.response.send_message(f"❌ You don't have enough coins. Your wallet: **{row['wallet']:,}**", ephemeral=True)
                return False
            
            # Deduct the bet
            await conn.execute(
                "UPDATE users SET wallet = wallet - $1 WHERE user_id = $2",
                bet,
                str(interaction.user.id)
            )
        
        return True

    async def payout(self, user_id: int, amount: int):
        """Adds winnings to the user's wallet."""
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET wallet = wallet + $1 WHERE user_id = $2",
                amount,
                str(user_id)
            )

    @app_commands.command(name="coinflip", description="Flip a coin for a 2x payout.")
    @app_commands.describe(bet="Amount to bet", side="Heads or Tails")
    @app_commands.choices(side=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, side: app_commands.Choice[str]):
        """Classic coin flip game."""
        if not await self.process_bet(interaction, bet):
            return
        
        result = random.choice(["heads", "tails"])
        
        await interaction.response.defer()
        await asyncio.sleep(1)
        
        if side.value == result:
            winnings = bet * 2
            await self.payout(interaction.user.id, winnings)
            await interaction.followup.send(
                f"🪙 **Coin landed on {result.upper()}!** You win **{winnings:,}** coins! 🎉"
            )
        else:
            await interaction.followup.send(
                f"🪙 **Coin landed on {result.upper()}!** You picked {side.value.upper()}. You lost **{bet:,}** coins. ❌"
            )

    @app_commands.command(name="slots", description="Spin the slots for a chance to win big.")
    @app_commands.describe(bet="Amount to bet")
    async def slots(self, interaction: discord.Interaction, bet: int):
        """Slots machine game."""
        if not await self.process_bet(interaction, bet):
            return
        
        symbols = ["🍎", "🍊", "🍋", "🍌", "🍇", "⭐"]
        
        await interaction.response.defer()
        await asyncio.sleep(1)
        
        spin1 = random.choice(symbols)
        spin2 = random.choice(symbols)
        spin3 = random.choice(symbols)
        
        result = f"🎰 **{spin1} | {spin2} | {spin3}**"
        
        if spin1 == spin2 == spin3:
            if spin1 == "⭐":
                winnings = bet * 10
                msg = f"{result}\n🎊 **JACKPOT!!!** Three stars! You win **{winnings:,}** coins!"
            else:
                winnings = bet * 5
                msg = f"{result}\n🎉 **WIN!** Three matches! You win **{winnings:,}** coins!"
            await self.payout(interaction.user.id, winnings)
        elif spin1 == spin2 or spin2 == spin3:
            winnings = bet * 2
            msg = f"{result}\n✨ **Two matches!** You win **{winnings:,}** coins!"
            await self.payout(interaction.user.id, winnings)
        else:
            msg = f"{result}\n❌ No matches. You lost **{bet:,}** coins."
        
        await interaction.followup.send(msg)

    @app_commands.command(name="blackjack", description="Play blackjack against the dealer.")
    @app_commands.describe(bet="Amount to bet")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        """Simple blackjack game."""
        if not await self.process_bet(interaction, bet):
            return
        
        await interaction.response.defer()
        await asyncio.sleep(1)
        
        # Simplified blackjack
        player_cards = [random.randint(1, 11), random.randint(1, 11)]
        dealer_cards = [random.randint(1, 11), random.randint(1, 11)]
        
        player_total = sum(player_cards)
        dealer_total = sum(dealer_cards)
        
        if player_total > 21:
            msg = f"🃏 Your hand: {player_total}\n💥 **BUST!** You went over 21. Lost **{bet:,}** coins."
        elif dealer_total > 21:
            winnings = bet * 2
            msg = f"🃏 Your hand: {player_total}\n🃏 Dealer busted at {dealer_total}! You win **{winnings:,}** coins!"
            await self.payout(interaction.user.id, winnings)
        elif player_total > dealer_total:
            winnings = bet * 2
            msg = f"🃏 Your hand: {player_total}\n🃏 Dealer: {dealer_total}\n🎉 You win **{winnings:,}** coins!"
            await self.payout(interaction.user.id, winnings)
        elif player_total == dealer_total:
            winnings = bet
            msg = f"🃏 Your hand: {player_total}\n🃏 Dealer: {dealer_total}\n🤝 Push! Your bet returned: **{winnings:,}** coins."
            await self.payout(interaction.user.id, winnings)
        else:
            msg = f"🃏 Your hand: {player_total}\n🃏 Dealer: {dealer_total}\n❌ Dealer wins. Lost **{bet:,}** coins."
        
        await interaction.followup.send(msg)

    @app_commands.command(name="roulette", description="Spin the roulette wheel.")
    @app_commands.describe(bet="Amount to bet", color="Red or Black")
    @app_commands.choices(color=[
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Black", value="black")
    ])
    async def roulette(self, interaction: discord.Interaction, bet: int, color: app_commands.Choice[str]):
        """Roulette wheel game."""
        if not await self.process_bet(interaction, bet):
            return
        
        result = random.choice(["red"] * 18 + ["black"] * 18 + ["green"])  # 37 slots
        
        await interaction.response.defer()
        await asyncio.sleep(1)
        
        if result == "green":
            msg = f"🎡 **Landed on GREEN (0)!** House always wins. Lost **{bet:,}** coins. 😱"
        elif color.value == result:
            winnings = bet * 2
            msg = f"🎡 **Landed on {result.upper()}!** You win **{winnings:,}** coins! 🎉"
            await self.payout(interaction.user.id, winnings)
        else:
            msg = f"🎡 **Landed on {result.upper()}!** You picked {color.value.upper()}. Lost **{bet:,}** coins. ❌"
        
        await interaction.followup.send(msg)

    @app_commands.command(name="crash", description="Multiplier rises dynamically. Cash out before it crashes!")
    @app_commands.describe(bet="Amount to wager", target="Target multiplier (e.g., 2.5 for 2.5x)")
    async def crash(self, interaction: discord.Interaction, bet: int, target: float):
        """Crash game with dynamic multiplier."""
        if target <= 1.0:
            await interaction.response.send_message("❌ Target multiplier must be higher than 1.0x.", ephemeral=True)
            return
        
        if not await self.process_bet(interaction, bet):
            return
        
        await interaction.response.defer()
        
        # Calculate when it crashes (weighted random)
        crash_point = round(random.choices(
            [random.uniform(1.0, 1.5), random.uniform(1.5, 5.0), random.uniform(5.0, 20.0)],
            weights=[60, 35, 5], k=1
        )[0], 2)
        
        if target <= crash_point:
            winnings = int(bet * target)
            msg = f"📈 **Cashout Successful!** Chart rose to **{crash_point:.2f}x**. You cashed out at **{target:.2f}x**, winning **{winnings:,}** coins! 🎉"
            await self.payout(interaction.user.id, winnings)
        else:
            msg = f"💥 **CRASHED!** Chart crashed at **{crash_point:.2f}x** before your target of **{target:.2f}x**. You lost **{bet:,}** coins. 😭"
        
        await interaction.followup.send(msg)

    @app_commands.command(name="horserace", description="Bet on horses in an epic race.")
    @app_commands.describe(bet="Amount to bet", horse="Which horse to bet on")
    @app_commands.choices(horse=[
        app_commands.Choice(name="Thunderbolt", value="Thunderbolt"),
        app_commands.Choice(name="Star Blazer", value="Star Blazer"),
        app_commands.Choice(name="Midnight Rush", value="Midnight Rush"),
        app_commands.Choice(name="Platinum Hoof", value="Platinum Hoof")
    ])
    async def horserace(self, interaction: discord.Interaction, bet: int, horse: app_commands.Choice[str]):
        """Horse racing game."""
        if not await self.process_bet(interaction, bet):
            return
        
        await interaction.response.defer()
        
        msg_obj = await interaction.followup.send("🏁 **THE RACE BEGINS!**")
        
        updates = [
            "🏇 *Thunderbolt takes the early lead! Star Blazer is close behind!*",
            "🏇 *Midnight Rush makes a fast move on the final stretch!*",
            "🏇 *Platinum Hoof is charging hard!*",
        ]
        
        for update in updates:
            await asyncio.sleep(1.5)
            await msg_obj.edit(content=update)
        
        winners = ["Thunderbolt", "Star Blazer", "Midnight Rush", "Platinum Hoof"]
        winning_horse = random.choice(winners)
        
        if horse.value == winning_horse:
            winnings = bet * 4
            await self.payout(interaction.user.id, winnings)
            res = f"🏆 **{winning_horse} Won the Race!** Your champion took first place! You won **{winnings:,}** coins! 🎉"
        else:
            res = f"❌ **{winning_horse} Won the Race!** Your horse, {horse.value}, fell behind. You lost **{bet:,}** coins."
        
        await msg_obj.edit(content=res)

    @app_commands.command(name="dice", description="Roll the dice (1-6 or 1-100).")
    @app_commands.describe(bet="Amount to bet", sides="How many sides (6 or 100)")
    async def dice(self, interaction: discord.Interaction, bet: int, sides: int):
        """Dice rolling game."""
        if sides not in [6, 100]:
            await interaction.response.send_message("❌ Sides must be 6 or 100.", ephemeral=True)
            return
        
        if not await self.process_bet(interaction, bet):
            return
        
        await interaction.response.defer()
        await asyncio.sleep(1)
        
        roll = random.randint(1, sides)
        threshold = sides // 2
        
        if roll > threshold:
            winnings = bet * 2
            msg = f"🎲 **You rolled {roll}!** Over {threshold}. You win **{winnings:,}** coins! 🎉"
            await self.payout(interaction.user.id, winnings)
        else:
            msg = f"🎲 **You rolled {roll}!** {threshold} or under. You lost **{bet:,}** coins. ❌"
        
        await interaction.followup.send(msg)

    @app_commands.command(name="lottery", description="Buy a lottery ticket for a massive jackpot.")
    @app_commands.describe(ticket_cost="Cost per ticket")
    async def lottery(self, interaction: discord.Interaction, ticket_cost: int):
        """Lottery game with minimal odds but huge payout."""
        if not await self.process_bet(interaction, ticket_cost):
            return
        
        await interaction.response.defer()
        await asyncio.sleep(1)
        
        # 0.1% chance to win (1 in 1000)
        if random.random() < 0.001:
            jackpot = ticket_cost * 10000
            msg = f"🎰 **LOTTERY WINNER!!!** 🎉\nYou won the jackpot: **{jackpot:,}** coins! 🤑"
            await self.payout(interaction.user.id, jackpot)
        else:
            msg = f"❌ Better luck next time! Your ticket didn't win. Lost **{ticket_cost:,}** coins."
        
        await interaction.followup.send(msg)

    @app_commands.command(name="gamble", description="All-in high-stakes gamble.")
    @app_commands.describe(bet="Amount to go all-in with")
    async def gamble(self, interaction: discord.Interaction, bet: int):
        """50/50 all-in gamble."""
        if not await self.process_bet(interaction, bet):
            return
        
        await interaction.response.defer()
        await asyncio.sleep(1)
        
        if random.random() < 0.5:
            winnings = bet * 2
            msg = f"💰 **ALL-IN GAMBLE WIN!** You doubled your bet! **+{winnings:,}** coins! 🎉"
            await self.payout(interaction.user.id, winnings)
        else:
            msg = f"💀 **ALL-IN GAMBLE LOSS!** You lost your **{bet:,}** coins betting it all! 😭"
        
        await interaction.followup.send(msg)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle command errors globally."""
        if isinstance(error, app_commands.CommandOnCooldown):
            remaining = int(error.retry_after)
            await interaction.response.send_message(
                f"⏳ **Cooldown:** Try again in {remaining} seconds.",
                ephemeral=True
            )
        else:
            logger.error(f"Command error: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred: {str(error)[:100]}",
                    ephemeral=True
                )

async def setup(bot: commands.Bot):
    await bot.add_cog(Gambling(bot))
    logger.info("Gambling cog loaded")
