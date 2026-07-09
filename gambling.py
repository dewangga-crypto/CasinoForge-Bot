# -*- coding: utf-8 -*-
"""
CasinoForge - Core Gambling Module
"""

import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class BlackjackView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, bet: int, cog):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.bet = bet
        self.cog = cog
        self.deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        self.player_hand = [self.draw_card(), self.draw_card()]
        self.dealer_hand = [self.draw_card(), self.draw_card()]

    def draw_card(self):
        return self.deck.pop(random.randint(0, len(self.deck) - 1))

    def get_hand_value(self, hand):
        val = sum(hand)
        aces = hand.count(11)
        while val > 21 and aces:
            val -= 10
            aces -= 1
        return val

    def make_embed(self, finished=False):
        embed = discord.Embed(title="🃏 Blackjack Table", color=discord.Color.blurple())
        p_val = self.get_hand_value(self.player_hand)
        d_val = self.get_hand_value(self.dealer_hand)
        
        embed.add_field(name="Your Hand", value=f"Cards: {self.player_hand}\nTotal: **{p_val}**", inline=True)
        if finished:
            embed.add_field(name="Dealer Hand", value=f"Cards: {self.dealer_hand}\nTotal: **{d_val}**", inline=True)
        else:
            embed.add_field(name="Dealer Hand", value=f"Cards: [{self.dealer_hand[0]}, ?]", inline=True)
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ This is not your blackjack table.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player_hand.append(self.draw_card())
        p_val = self.get_hand_value(self.player_hand)
        
        if p_val > 21:
            for child in self.children: child.disabled = True
            await interaction.response.edit_message(content=f"💥 **Bust!** You went over 21. Lost **{self.bet:,}** coins.", embed=self.make_embed(True), view=self)
            self.stop()
        else:
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children: child.disabled = True
        
        d_val = self.get_hand_value(self.dealer_hand)
        while d_val < 17:
            self.dealer_hand.append(self.draw_card())
            d_val = self.get_hand_value(self.dealer_hand)
            
        p_val = self.get_hand_value(self.player_hand)
        
        if d_val > 21:
            winnings = self.bet * 2
            await self.cog.payout(interaction.user.id, winnings)
            msg = f"🎉 Dealer busted! You won **{winnings:,}** coins!"
        elif p_val > d_val:
            winnings = self.bet * 2
            await self.cog.payout(interaction.user.id, winnings)
            msg = f"🎉 You beat the dealer! You won **{winnings:,}** coins!"
        elif p_val < d_val:
            msg = f"❌ Dealer wins. You lost **{self.bet:,}** coins."
        else:
            await self.cog.payout(interaction.user.id, self.bet)
            msg = "👔 It's a tie! Your bet has been refunded."
            
        await interaction.response.edit_message(content=msg, embed=self.make_embed(True), view=self)
        self.stop()


class HigherLowerView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, bet: int, cog):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.bet = bet
        self.cog = cog
        self.current_card = random.randint(1, 13)
        self.card_names = {1: "Ace", 11: "Jack", 12: "Queen", 13: "King"}

    def get_card_name(self, val):
        return self.card_names.get(val, str(val))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Interact with your own command.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Higher 📈", style=discord.ButtonStyle.blurple)
    async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "higher")

    @discord.ui.button(label="Lower 📉", style=discord.ButtonStyle.blurple)
    async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "lower")

    async def process_choice(self, interaction: discord.Interaction, guess):
        for child in self.children: child.disabled = True
        next_card = random.randint(1, 13)
        
        win = False
        if guess == "higher" and next_card >= self.current_card: win = True
        elif guess == "lower" and next_card <= self.current_card: win = True
        
        old_name = self.get_card_name(self.current_card)
        new_name = self.get_card_name(next_card)
        
        if win:
            winnings = self.bet * 2
            await self.cog.payout(interaction.user.id, winnings)
            msg = f"✅ Correct! The next card was a **{new_name}** (was {old_name}). You won **{winnings:,}** coins!"
        else:
            msg = f"❌ Wrong! The next card was a **{new_name}** (was {old_name}). You lost **{self.bet:,}** coins."
            
        await interaction.response.edit_message(content=msg, view=self)
        self.stop()


class Gambling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ensure_user(self, user_id: int):
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING;",
                str(user_id)
            )

    # Core helper function to process all bets securely
    async def process_bet(self, interaction: discord.Interaction, bet: int) -> bool:
        """Deducts the bet and checks for restrictions. Returns True if successful."""
        if bet <= 0:
            await interaction.response.send_message("❌ You must bet a positive amount.", ephemeral=True)
            return False

        await self.ensure_user(interaction.user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet, is_frozen, is_blacklisted FROM users WHERE user_id = $1", str(interaction.user.id))
            
            if row['is_blacklisted'] or row['is_frozen']:
                await interaction.response.send_message("❌ Your account is restricted from gambling.", ephemeral=True)
                return False
                
            if row['wallet'] < bet:
                await interaction.response.send_message(f"❌ Insufficient funds. You only have **{row['wallet']:,}** coins.", ephemeral=True)
                return False
                
            # Temporarily deduct the bet. If they win, we pay them back + winnings later.
            await conn.execute("UPDATE users SET wallet = wallet - $1 WHERE user_id = $2", bet, str(interaction.user.id))
            return True

    async def payout(self, user_id: int, amount: int):
        """Adds winnings to the user's wallet."""
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET wallet = wallet + $1 WHERE user_id = $2", amount, str(user_id))

    # 1. /coinflip
    @app_commands.command(name="coinflip", description="Flip a coin for a 2x payout.")
    @app_commands.describe(bet="Amount to bet", side="Heads or Tails")
    @app_commands.choices(side=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, side: app_commands.Choice[str]):
        if not await self.process_bet(interaction, bet): return
        
        result = random.choice(["heads", "tails"])
        
        if side.value == result:
            winnings = bet * 2
            await self.payout(interaction.user.id, winnings)
            msg = f"🪙 The coin landed on **{result.title()}**! You won **{winnings:,}** coins!"
        else:
            msg = f"🪙 The coin landed on **{result.title()}**... You lost your bet of **{bet:,}**."
            
        await interaction.response.send_message(msg)

    # 2. /slots
    @app_commands.command(name="slots", description="Spin the slot machine. Matches multiply your bet.")
    async def slots(self, interaction: discord.Interaction, bet: int):
        if not await self.process_bet(interaction, bet): return
        
        emojis = ["🍒", "🍋", "🍉", "⭐", "💎", "7️⃣"]
        spin = [random.choice(emojis) for _ in range(3)]
        
        if spin[0] == spin[1] == spin[2]:
            multiplier = 10 if spin[0] == "7️⃣" else 5
            winnings = bet * multiplier
            await self.payout(interaction.user.id, winnings)
            result_msg = f"🎰 **JACKPOT!** {multiplier}x Payout! You won **{winnings:,}** coins!"
        elif spin[0] == spin[1] or spin[1] == spin[2] or spin[0] == spin[2]:
            winnings = bet * 2
            await self.payout(interaction.user.id, winnings)
            result_msg = f"🎰 **Minor Win!** 2x Payout! You won **{winnings:,}** coins!"
        else:
            result_msg = f"🎰 **Bust!** You lost **{bet:,}** coins."

        embed = discord.Embed(title="Slot Machine", description=f"| {' | '.join(spin)} |", color=discord.Color.gold())
        embed.add_field(name="Result", value=result_msg)
        await interaction.response.send_message(embed=embed)

    # 3. /dice
    @app_commands.command(name="dice", description="Roll two dice. Guess Over, Under, or Exact 7.")
    @app_commands.choices(prediction=[
        app_commands.Choice(name="Over 7 (2x)", value="over"),
        app_commands.Choice(name="Under 7 (2x)", value="under"),
        app_commands.Choice(name="Exact 7 (4x)", value="exact")
    ])
    async def dice(self, interaction: discord.Interaction, bet: int, prediction: app_commands.Choice[str]):
        if not await self.process_bet(interaction, bet): return
        
        die1, die2 = random.randint(1, 6), random.randint(1, 6)
        total = die1 + die2
        
        win = False
        winnings = 0
        
        if prediction.value == "over" and total > 7:
            win, winnings = True, bet * 2
        elif prediction.value == "under" and total < 7:
            win, winnings = True, bet * 2
        elif prediction.value == "exact" and total == 7:
            win, winnings = True, bet * 4
            
        if win:
            await self.payout(interaction.user.id, winnings)
            msg = f"🎲 You rolled a **{die1}** and **{die2}** (Total: {total}).\nYou guessed `{prediction.name}` and WON **{winnings:,}** coins!"
        else:
            msg = f"🎲 You rolled a **{die1}** and **{die2}** (Total: {total}).\nYou guessed `{prediction.name}` and lost **{bet:,}** coins."
            
        await interaction.response.send_message(msg)

    # 4. /rps
    @app_commands.command(name="rps", description="Rock, Paper, Scissors for cash.")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock 🪨", value="rock"),
        app_commands.Choice(name="Paper 📄", value="paper"),
        app_commands.Choice(name="Scissors ✂️", value="scissors")
    ])
    async def rps(self, interaction: discord.Interaction, bet: int, choice: app_commands.Choice[str]):
        if not await self.process_bet(interaction, bet): return
        
        bot_choice = random.choice(["rock", "paper", "scissors"])
        user_c = choice.value
        
        if user_c == bot_choice:
            await self.payout(interaction.user.id, bet) # Refund on tie
            msg = f"🤖 Bot chose **{bot_choice}**. It's a **TIE**! Your **{bet:,}** coins were refunded."
        elif (user_c == "rock" and bot_choice == "scissors") or \
             (user_c == "paper" and bot_choice == "rock") or \
             (user_c == "scissors" and bot_choice == "paper"):
            winnings = bet * 2
            await self.payout(interaction.user.id, winnings)
            msg = f"🤖 Bot chose **{bot_choice}**. You **WON** **{winnings:,}** coins!"
        else:
            msg = f"🤖 Bot chose **{bot_choice}**. You **LOST** **{bet:,}** coins."
            
        await interaction.response.send_message(msg)

    # 5. /cups
    @app_commands.command(name="cups", description="Guess which cup hides the ball (1/3 chance for 3x payout).")
    @app_commands.describe(cup="Pick Cup 1, 2, or 3")
    async def cups(self, interaction: discord.Interaction, bet: int, cup: int):
        if cup not in [1, 2, 3]:
            return await interaction.response.send_message("❌ You must pick cup 1, 2, or 3.", ephemeral=True)
            
        if not await self.process_bet(interaction, bet): return
        
        winning_cup = random.randint(1, 3)
        
        if cup == winning_cup:
            winnings = bet * 3
            await self.payout(interaction.user.id, winnings)
            msg = f"🥤 🥤 🥤\nThe ball was in **Cup {winning_cup}**! You chose wisely and won **{winnings:,}** coins!"
        else:
            msg = f"🥤 🥤 🥤\nThe ball was in **Cup {winning_cup}**. You chose {cup} and lost **{bet:,}** coins."
            
        await interaction.response.send_message(msg)

    # 6. /scratch
    @app_commands.command(name="scratch", description="Buy a scratch card. Reveal 3 matching symbols to win.")
    async def scratch(self, interaction: discord.Interaction, bet: int):
        if not await self.process_bet(interaction, bet): return
        
        symbols = ["🍎", "💰", "💀", "💎"]
        grid = [random.choice(symbols) for _ in range(3)]
        
        if grid[0] == grid[1] == grid[2]:
            if grid[0] == "💀":
                msg = "You scratched 3 Skulls... You lose absolutely everything."
            else:
                multiplier = 5 if grid[0] == "💎" else 3
                winnings = bet * multiplier
                await self.payout(interaction.user.id, winnings)
                msg = f"**MATCH!** You scratched 3 {grid[0]} and won **{winnings:,}** coins!"
        else:
            msg = f"No match. Better luck next time. You lost **{bet:,}** coins."

        # Discord spoiler tags act as the "scratching" mechanic
        scratch_pad = f"||{grid[0]}|| - ||{grid[1]}|| - ||{grid[2]}||"
        
        embed = discord.Embed(title="🎟️ Scratch Card", description=scratch_pad, color=discord.Color.brand_green())
        embed.add_field(name="Result", value=msg)
        await interaction.response.send_message(embed=embed)

    # 7. /all-in
    @app_commands.command(name="all-in", description="Gamble your ENTIRE wallet on a single 50/50 coinflip.")
    async def all_in(self, interaction: discord.Interaction):
        await self.ensure_user(interaction.user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            wallet = await conn.fetchval("SELECT wallet FROM users WHERE user_id = $1 AND is_frozen = FALSE", str(interaction.user.id))
            
            if not wallet or wallet <= 0:
                return await interaction.response.send_message("❌ You are completely broke. You have nothing to go all-in with.", ephemeral=True)
                
            # Deduct the whole wallet
            await conn.execute("UPDATE users SET wallet = 0 WHERE user_id = $1", str(interaction.user.id))
            
        result = random.choice([True, False])
        
        if result:
            winnings = wallet * 2
            await self.payout(interaction.user.id, winnings)
            await interaction.response.send_message(f"🔥 **ALL IN SUCCESS!** You risked it all and doubled your money to **{winnings:,}** coins!")
        else:
            await interaction.response.send_message(f"💀 **BANKRUPT!** You risked **{wallet:,}** coins on an all-in and lost everything.")

    # 8. /daily-spin
    @app_commands.command(name="daily-spin", description="Spin the daily wheel for free coins.")
    @app_commands.checks.cooldown(1, 86400, key=lambda i: i.user.id) # 24 hours
    async def daily_spin(self, interaction: discord.Interaction):
        await self.ensure_user(interaction.user.id)
        
        rewards = [1000, 2500, 5000, 500, 100, 10000]
        weights = [40, 25, 10, 15, 9, 1] # 1% chance for 10k
        win_amount = random.choices(rewards, weights=weights, k=1)[0]
        
        await self.payout(interaction.user.id, win_amount)
        await interaction.response.send_message(f"🎡 You spun the daily wheel and won **{win_amount:,}** coins! Come back tomorrow.")

    @app_commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            import datetime
            remaining = str(datetime.timedelta(seconds=int(error.retry_after)))
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⏳ **Cooldown:** You've already used this. Try again in `{remaining}`.", ephemeral=True)
        else:
            raise error

async def setup(bot: commands.Bot):
    await bot.add_cog(Gambling(bot))
    # 9. /blackjack
    @app_commands.command(name="blackjack", description="Play a hand of blackjack against the dealer.")
    @app_commands.describe(bet="Amount to wager")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        if not await self.process_bet(interaction, bet): return
        view = BlackjackView(interaction, bet, self)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

    # 10. /higherlower
    @app_commands.command(name="higherlower", description="Guess if the next card will be higher or lower.")
    @app_commands.describe(bet="Amount to wager")
    async def higherlower(self, interaction: discord.Interaction, bet: int):
        if not await self.process_bet(interaction, bet): return
        view = HigherLowerView(interaction, bet, self)
        await interaction.response.send_message(f"🃏 Current Card: **{view.get_card_name(view.current_card)}**. Will the next card be higher or lower?", view=view)

    # 11. /roulette
    @app_commands.command(name="roulette", description="Bet on red, black, or specific number ranges.")
    @app_commands.describe(bet="Amount to wager", space="Where to place your bet")
    @app_commands.choices(space=[
        app_commands.Choice(name="Red (2x)", value="red"),
        app_commands.Choice(name="Black (2x)", value="black"),
        app_commands.Choice(name="Evens (2x)", value="evens"),
        app_commands.Choice(name="Odds (2x)", value="odds")
    ])
    async def roulette(self, interaction: discord.Interaction, bet: int, space: app_commands.Choice[str]):
        if not await self.process_bet(interaction, bet): return
        
        roll = random.randint(0, 36)
        color = "red" if roll % 2 == 0 else "black"
        if roll == 0: color = "green"
        
        win = False
        if space.value == color: win = True
        elif space.value == "evens" and roll % 2 == 0 and roll != 0: win = True
        elif space.value == "odds" and roll % 2 != 0: win = True
        
        if win:
            winnings = bet * 2
            await self.payout(interaction.user.id, winnings)
            msg = f"🎡 The wheel spun and landed on **{roll} ({color.title()})**! You won **{winnings:,}** coins!"
        else:
            msg = f"🎡 The wheel spun and landed on **{roll} ({color.title()})**... You lost your bet of **{bet:,}**."
            
        await interaction.response.send_message(msg)

    # 12. /crash
    @app_commands.command(name="crash", description="Multiplier rises dynamically. Set your cashout target before it crashes.")
    @app_commands.describe(bet="Amount to wager", target="Target multiplier to cashout (e.g., 2 for 2.0x)")
    async def crash(self, interaction: discord.Interaction, bet: int, target: float):
        if target <= 1.0:
            return await interaction.response.send_message("❌ Target multiplier must be higher than 1.0x.", ephemeral=True)
        if not await self.process_bet(interaction, bet): return
        
        # Calculate when it crashes (exponential scaling)
        crash_point = round(random.choices(
            [random.uniform(1.0, 1.5), random.uniform(1.5, 5.0), random.uniform(5.0, 20.0)],
            weights=[60, 35, 5], k=1
        )[0], 2)
        
        if target <= crash_point:
            winnings = int(bet * target)
            await self.payout(interaction.user.id, winnings)
            msg = f"📈 **📈 Cashout Successful!** The chart rose to **{crash_point:.2f}x** before crashing. You cashed out safely at your target of **{target:.2f}x**, winning **{winnings:,}** coins!"
        else:
            msg = f"💥 **CRASHED!** The chart abruptly crashed at **{crash_point:.2f}x** before reaching your target of **{target:.2f}x**. You lost **{bet:,}** coins."
            
        await interaction.response.send_message(msg)

    # 13. /wheel
    @app_commands.command(name="wheel", description="Spin the risk wheel for variable payout multipliers.")
    @app_commands.describe(bet="Amount to wager")
    async def wheel(self, interaction: discord.Interaction, bet: int):
        if not await self.process_bet(interaction, bet): return
        
        sectors = [0.0, 0.5, 1.0, 1.5, 2.0, 5.0]
        weights = [25, 25, 20, 15, 10, 5]
        multiplier = random.choices(sectors, weights=weights, k=1)[0]
        
        winnings = int(bet * multiplier)
        if winnings > 0:
            await self.payout(interaction.user.id, winnings)
            
        if multiplier > 1.0:
            msg = f"🎡 The wheel clicked to a **{multiplier}x** sector! You won **{winnings:,}** coins!"
        elif multiplier == 1.0:
            msg = "🎡 The wheel clicked to a **1.0x** sector. You broke even and kept your coins."
        else:
            msg = f"🎡 The wheel clicked to a **{multiplier}x** sector... You lost **{bet - winnings:,}** coins."
            
        await interaction.response.send_message(msg)

    # 14. /horse-race
    @app_commands.command(name="horse-race", description="Place a bet on one of four racing horses.")
    @app_commands.describe(bet="Amount to wager", horse="Pick your racing champion")
    @app_commands.choices(horse=[
        app_commands.Choice(name="⚡ Thunderbolt", value="Thunderbolt"),
        app_commands.Choice(name="🔥 Star Blazer", value="Star Blazer"),
        app_commands.Choice(name="💨 Midnight Rush", value="Midnight Rush"),
        app_commands.Choice(name="💎 Platinum Hoof", value="Platinum Hoof")
    ])
    async def horse_race(self, interaction: discord.Interaction, bet: int, horse: app_commands.Choice[str]):
        if not await self.process_bet(interaction, bet): return
        
        await interaction.response.send_message("🏁 The gates fly open! The horses are running...")
        msg = await interaction.original_response()
        
        # Fast simulated racing text updates
        await asyncio.sleep(1.5)
        await msg.edit(content="🏇 *Thunderbolt takes an early lead! Star Blazer is close behind!*")
        await asyncio.sleep(1.5)
        await msg.edit(content="🏇 *Midnight Rush makes a fast turn around the final corner!*")
        await asyncio.sleep(1.5)
        
        winners = ["Thunderbolt", "Star Blazer", "Midnight Rush", "Platinum Hoof"]
        winning_horse = random.choice(winners)
        
        if horse.value == winning_horse:
            winnings = bet * 4
            await self.payout(interaction.user.id, winnings)
            res = f"🏆 **{winning_horse} Won the Race!** Your champion took first place! You won **{winnings:,}** coins!"
        else:
            res = f"❌ **{winning_horse} Won the Race!** Your horse, {horse.name}, fell behind. You lost **{bet:,}** coins."
            
        await msg.edit(content=res)

    # 15. /lottery
    @app_commands.command(name="lottery", description="Buy tickets for a server drawing. The more tickets you hold, the higher your win odds.")
    @app_commands.describe(tickets="Number of tickets to purchase (100 coins per ticket)")
    async def lottery(self, interaction: discord.Interaction, tickets: int):
        if tickets <= 0:
            return await interaction.response.send_message("❌ You must buy at least 1 ticket.", ephemeral=True)
            
        cost = tickets * 100
        if not await self.process_bet(interaction, cost): return
        
        # Instant random lottery sweepstakes simulation
        win_chance = min(90.0, tickets * 0.5) # Caps mechanical luck chance at 90%
        roll = random.uniform(0, 100)
        
        if roll <= win_chance:
            jackpot = cost * random.randint(3, 8)
            await self.payout(interaction.user.id, jackpot)
            msg = f"🎟️ You purchased **{tickets}** tickets (Odds: {win_chance:.1f}%).\n🎉 **JACKPOT!** Your ticket number was pulled from the drum! You won **{jackpot:,}** coins!"
        else:
            msg = f"🎟️ You purchased **{tickets}** tickets (Odds: {win_chance:.1f}%).\n❌ None of your numbers matched the winning drawing ticket. Better luck next time!"
            
        await interaction.response.send_message(msg)
