# -*- coding: utf-8 -*-
"""
CasinoForge - Economy Action Module
"""

import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncpg

# --- UI Components for Interactive Commands ---

class GiveConfirmView(discord.ui.View):
    def __init__(self, sender: discord.User, target: discord.User, amount: int, db_pool):
        super().__init__(timeout=60)
        self.sender = sender
        self.target = target
        self.amount = amount
        self.db_pool = db_pool

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.sender.id:
            await interaction.response.send_message("❌ You cannot confirm someone else's transaction.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm Transfer", style=discord.ButtonStyle.green, custom_id="give_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        async with self.db_pool.acquire() as conn:
            # We use a database transaction to ensure money isn't duplicated if an error occurs mid-transfer
            async with conn.transaction():
                sender_bal = await conn.fetchval("SELECT wallet FROM users WHERE user_id = $1 AND is_frozen = FALSE AND is_blacklisted = FALSE", str(self.sender.id))
                
                if sender_bal is None or sender_bal < self.amount:
                    await interaction.followup.send(f"❌ Transaction failed. {self.sender.mention}, you no longer have enough funds or your account was frozen.", ephemeral=True)
                    self.stop()
                    return

                # Deduct from sender, add to target (creates target row if they don't exist)
                await conn.execute("UPDATE users SET wallet = wallet - $1 WHERE user_id = $2", self.amount, str(self.sender.id))
                await conn.execute(
                    "INSERT INTO users (user_id, wallet) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET wallet = users.wallet + $2",
                    str(self.target.id), self.amount
                )
        
        # Disable buttons after use
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(content=f"✅ **Transfer Complete:** {self.sender.mention} successfully gave **{self.amount:,}** coins to {self.target.mention}.", view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="give_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🛑 **Transfer Cancelled.**", view=self)
        self.stop()

class RequestConfirmView(discord.ui.View):
    def __init__(self, requester: discord.User, target: discord.User, amount: int, db_pool):
        super().__init__(timeout=300) # 300 seconds = 5 minutes expiration
        self.requester = requester
        self.target = target
        self.amount = amount
        self.db_pool = db_pool

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(f"❌ Only {self.target.mention} can accept or deny this request.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accept Request", style=discord.ButtonStyle.green, custom_id="req_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                target_bal = await conn.fetchval("SELECT wallet FROM users WHERE user_id = $1 AND is_frozen = FALSE AND is_blacklisted = FALSE", str(self.target.id))
                
                if target_bal is None or target_bal < self.amount:
                    await interaction.followup.send("❌ You do not have enough coins in your wallet to accept this request, or your account is frozen.", ephemeral=True)
                    return

                await conn.execute("UPDATE users SET wallet = wallet - $1 WHERE user_id = $2", self.amount, str(self.target.id))
                await conn.execute(
                    "INSERT INTO users (user_id, wallet) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET wallet = users.wallet + $2",
                    str(self.requester.id), self.amount
                )

        for child in self.children:
            child.disabled = True
        await interaction.message.edit(content=f"✅ **Request Accepted:** {self.target.mention} paid **{self.amount:,}** coins to {self.requester.mention}.", embed=None, view=self)
        self.stop()

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="req_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"🛑 **Request Denied:** {self.target.mention} refused to pay {self.requester.mention}.", embed=None, view=self)
        self.stop()

    async def on_timeout(self):
        # Automatically disable if 5 minutes pass
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(content=f"⏳ **Request Expired:** The request from {self.requester.mention} to {self.target.mention} timed out after 5 minutes.", embed=None, view=self)
        except Exception:
            pass

# --- The Main Action Cog ---

class Action(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Helper method to initialize users in the database safely
    async def ensure_user(self, user_id: int):
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING;",
                str(user_id)
            )

    # 1. /give
    @app_commands.command(name="give", description="Give a specific amount of money to another player.")
    @app_commands.describe(user="The player to give money to", amount="The amount to send")
    async def give(self, interaction: discord.Interaction, user: discord.User, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ You must give a positive amount.", ephemeral=True)
        if user.id == interaction.user.id:
            return await interaction.response.send_message("❌ You cannot give money to yourself.", ephemeral=True)
        if user.bot:
            return await interaction.response.send_message("❌ You cannot give money to bots.", ephemeral=True)

        await self.ensure_user(interaction.user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet, is_frozen, is_blacklisted FROM users WHERE user_id = $1", str(interaction.user.id))
            
            if row['is_blacklisted'] or row['is_frozen']:
                return await interaction.response.send_message("❌ Your account is currently restricted.", ephemeral=True)
            if row['wallet'] < amount:
                return await interaction.response.send_message(f"❌ You do not have enough funds. Your balance is **{row['wallet']:,}**.", ephemeral=True)

        view = GiveConfirmView(interaction.user, user, amount, self.bot.db_pool)
        await interaction.response.send_message(
            f"⚠️ {interaction.user.mention}, are you sure you want to send **{amount:,}** coins to {user.mention}?",
            view=view
        )

    # 2. /request
    @app_commands.command(name="request", description="Send an interactive money request to another player.")
    @app_commands.describe(user="The player you are asking money from", amount="The amount you want")
    async def request_money(self, interaction: discord.Interaction, user: discord.User, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ You must request a positive amount.", ephemeral=True)
        if user.id == interaction.user.id:
            return await interaction.response.send_message("❌ You cannot request money from yourself.", ephemeral=True)
        if user.bot:
            return await interaction.response.send_message("❌ Bots don't have wallets.", ephemeral=True)

        await self.ensure_user(interaction.user.id)
        await self.ensure_user(user.id)

        embed = discord.Embed(
            title="💸 Incoming Payment Request",
            description=f"**{interaction.user.mention}** is requesting **{amount:,}** coins from you.",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="This request expires in 5 minutes.")

        view = RequestConfirmView(interaction.user, user, amount, self.bot.db_pool)
        await interaction.response.send_message(
            content=user.mention,
            embed=embed,
            view=view
        )
        # Attach the message to the view for timeout editing
        view.message = await interaction.original_response()

    # 3. /balance
    @app_commands.command(name="balance", description="Check your current wallet and bank balance.")
    @app_commands.describe(user="Optional: Check someone else's balance")
    async def balance(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        await self.ensure_user(target.id)

        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet, bank, bank_limit FROM users WHERE user_id = $1", str(target.id))
        
        embed = discord.Embed(title=f"💳 {target.display_name}'s Balance", color=discord.Color.blue())
        embed.add_field(name="Wallet", value=f"**{row['wallet']:,}** 🪙", inline=True)
        embed.add_field(name="Bank", value=f"**{row['bank']:,} / {row['bank_limit']:,}** 🏦", inline=True)
        
        net_worth = row['wallet'] + row['bank']
        embed.add_field(name="Net Worth", value=f"**{net_worth:,}**", inline=False)
        
        await interaction.response.send_message(embed=embed)

    # 4. /deposit
    @app_commands.command(name="deposit", description="Secure your wallet cash in the bank.")
    @app_commands.describe(amount="Amount to deposit (or type 0 to deposit ALL)")
    async def deposit(self, interaction: discord.Interaction, amount: int):
        if amount < 0:
            return await interaction.response.send_message("❌ Amount cannot be negative.", ephemeral=True)
            
        await self.ensure_user(interaction.user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT wallet, bank, bank_limit, is_frozen, is_blacklisted FROM users WHERE user_id = $1", str(interaction.user.id))
            
            if row['is_blacklisted'] or row['is_frozen']:
                return await interaction.response.send_message("❌ Your account is currently restricted.", ephemeral=True)

            deposit_amount = row['wallet'] if amount == 0 else amount
            
            if deposit_amount == 0:
                return await interaction.response.send_message("❌ You have no coins to deposit.", ephemeral=True)
            if row['wallet'] < deposit_amount:
                return await interaction.response.send_message("❌ You do not have that much in your wallet.", ephemeral=True)
                
            available_space = row['bank_limit'] - row['bank']
            if available_space <= 0:
                return await interaction.response.send_message("❌ Your bank is entirely full!", ephemeral=True)
                
            if deposit_amount > available_space:
                deposit_amount = available_space

            await conn.execute("UPDATE users SET wallet = wallet - $1, bank = bank + $1 WHERE user_id = $2", deposit_amount, str(interaction.user.id))
            
        await interaction.response.send_message(f"✅ Successfully deposited **{deposit_amount:,}** coins into your bank.")

    # 5. /withdraw
    @app_commands.command(name="withdraw", description="Pull cash out of your bank into your wallet.")
    @app_commands.describe(amount="Amount to withdraw (or type 0 to withdraw ALL)")
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        if amount < 0:
            return await interaction.response.send_message("❌ Amount cannot be negative.", ephemeral=True)

        await self.ensure_user(interaction.user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT bank, is_frozen, is_blacklisted FROM users WHERE user_id = $1", str(interaction.user.id))
            
            if row['is_blacklisted'] or row['is_frozen']:
                return await interaction.response.send_message("❌ Your account is currently restricted.", ephemeral=True)

            withdraw_amount = row['bank'] if amount == 0 else amount
            
            if withdraw_amount == 0:
                return await interaction.response.send_message("❌ You have no coins in your bank.", ephemeral=True)
            if row['bank'] < withdraw_amount:
                return await interaction.response.send_message("❌ You do not have that much in your bank.", ephemeral=True)

            await conn.execute("UPDATE users SET bank = bank - $1, wallet = wallet + $1 WHERE user_id = $2", withdraw_amount, str(interaction.user.id))
            
        await interaction.response.send_message(f"✅ Successfully withdrew **{withdraw_amount:,}** coins from your bank.")

    # 6. /work
    @app_commands.command(name="work", description="Work a standard job to earn some coins.")
    @app_commands.checks.cooldown(1, 3600, key=lambda i: i.user.id) # 1 hour cooldown
    async def work(self, interaction: discord.Interaction):
        await self.ensure_user(interaction.user.id)
        payout = 500 # Fixed payout for now, can be randomized later
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET wallet = wallet + $1 WHERE user_id = $2", payout, str(interaction.user.id))
            
        await interaction.response.send_message(f"💼 You worked hard and earned **{payout}** coins!")

    # 7. /beg
    @app_commands.command(name="beg", description="Beg for spare change on the streets.")
    @app_commands.checks.cooldown(1, 600, key=lambda i: i.user.id) # 10 minute cooldown
    async def beg(self, interaction: discord.Interaction):
        await self.ensure_user(interaction.user.id)
        payout = 50
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET wallet = wallet + $1 WHERE user_id = $2", payout, str(interaction.user.id))
            
        await interaction.response.send_message(f"🥺 Someone felt bad and tossed **{payout}** coins into your hat.")

    # 8. /rob
    @app_commands.command(name="rob", description="Attempt to steal coins from another player's wallet.")
    @app_commands.checks.cooldown(1, 7200, key=lambda i: i.user.id) # 2 hour cooldown
    @app_commands.describe(user="The player to rob")
    async def rob(self, interaction: discord.Interaction, user: discord.User):
        if user.id == interaction.user.id:
            return await interaction.response.send_message("❌ You cannot rob yourself.", ephemeral=True)
            
        await self.ensure_user(interaction.user.id)
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            target_bal = await conn.fetchval("SELECT wallet FROM users WHERE user_id = $1", str(user.id))
            
            if target_bal < 100:
                # Reset cooldown if target is too poor
                interaction.command.reset_cooldown(interaction)
                return await interaction.response.send_message(f"❌ {user.mention} is too poor to rob right now.", ephemeral=True)
                
            steal_amount = int(target_bal * 0.10) # Robs 10% of their wallet
            
            async with conn.transaction():
                await conn.execute("UPDATE users SET wallet = wallet - $1 WHERE user_id = $2", steal_amount, str(user.id))
                await conn.execute("UPDATE users SET wallet = wallet + $1 WHERE user_id = $2", steal_amount, str(interaction.user.id))
                
        await interaction.response.send_message(f"🥷 Sneaky! You successfully robbed **{steal_amount:,}** coins from {user.mention}!")

    # 9. /shop
    @app_commands.command(name="shop", description="View the global server shop.")
    async def shop(self, interaction: discord.Interaction):
        async with self.bot.db_pool.acquire() as conn:
            items = await conn.fetch("SELECT item_name, price FROM global_shop ORDER BY price ASC")
            
        if not items:
            return await interaction.response.send_message("🛒 The shop is currently empty.", ephemeral=True)
            
        embed = discord.Embed(title="🛒 Global Item Shop", color=discord.Color.purple())
        for row in items:
            embed.add_field(name=row['item_name'], value=f"**{row['price']:,}** 🪙", inline=False)
            
        await interaction.response.send_message(embed=embed)

    # 10. /buy (UPDATED TO HANDLE AUTO_COMMANDS)
    @app_commands.command(name="buy", description="Purchase an item from the shop.")
    @app_commands.describe(item="Name of the item to buy", quantity="Amount to purchase")
    async def buy(self, interaction: discord.Interaction, item: str, quantity: int = 1):
        if quantity <= 0:
            return await interaction.response.send_message("❌ Quantity must be at least 1.", ephemeral=True)
            
        await self.ensure_user(interaction.user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            # Now we fetch the auto_command alongside the price
            shop_item = await conn.fetchrow("SELECT price, auto_command, item_name FROM global_shop WHERE LOWER(item_name) = LOWER($1)", item)
            
            if not shop_item:
                return await interaction.response.send_message(f"❌ Item `{item}` does not exist in the shop.", ephemeral=True)
                
            total_cost = shop_item['price'] * quantity
            actual_name = shop_item['item_name']
            trigger = shop_item['auto_command']
            
            async with conn.transaction():
                user_wallet = await conn.fetchval("SELECT wallet FROM users WHERE user_id = $1", str(interaction.user.id))
                
                if user_wallet < total_cost:
                    return await interaction.response.send_message(f"❌ You need **{total_cost:,}** coins for this purchase.", ephemeral=True)
                    
                await conn.execute("UPDATE users SET wallet = wallet - $1 WHERE user_id = $2", total_cost, str(interaction.user.id))
                
                # Check if user already has the item in their inventory
                has_item = await conn.fetchval("SELECT id FROM inventories WHERE user_id = $1 AND LOWER(item_name) = LOWER($2)", str(interaction.user.id), item)
                
                if has_item:
                    await conn.execute("UPDATE inventories SET quantity = quantity + $1 WHERE id = $2", quantity, has_item)
                else:
                    await conn.execute("INSERT INTO inventories (user_id, item_name, quantity) VALUES ($1, $2, $3)", str(interaction.user.id), actual_name, quantity)
                    
        await interaction.response.send_message(f"🛍️ You successfully purchased **{quantity}x {actual_name}** for **{total_cost:,}** coins!")
        
        # If there is an auto-command attached to this item, format it and send it to the channel
        if trigger:
            formatted_command = trigger.replace("{user}", interaction.user.mention)
            
            # We send this as a follow-up without the ephemeral tag so it goes into the public chat
            await interaction.channel.send(formatted_command)
