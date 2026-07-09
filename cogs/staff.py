# -*- coding: utf-8 -*-
"""
CasinoForge - Economy Management & Staff Module
"""

import discord
from discord import app_commands
from discord.ext import commands

class Staff(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ensure_user(self, user_id: int):
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING;",
                str(user_id)
            )

    # 1. /shop-add (UPDATED WITH AUTO-COMMAND)
    @app_commands.command(name="shop-add", description="[Admin] Add a new item or rank to the global shop.")
    @app_commands.describe(
        item_name="Name of the item (e.g., VIP Rank)", 
        price="Cost in coins",
        auto_command="Optional: Text/Command to trigger in chat on purchase. Use {user} to ping the buyer."
    )
    @app_commands.default_permissions(administrator=True)
    async def shop_add(self, interaction: discord.Interaction, item_name: str, price: int, auto_command: str = None):
        if price < 0:
            return await interaction.response.send_message("❌ Price cannot be negative.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO global_shop (item_name, price, auto_command) 
                VALUES ($1, $2, $3) 
                ON CONFLICT (item_name) 
                DO UPDATE SET price = $2, auto_command = $3;
                """,
                item_name, price, auto_command
            )
        
        msg = f"✅ **Shop Updated:** Added/Updated `{item_name}` for **{price:,}** coins."
        if auto_command:
            msg += f"\n⚙️ **Auto-Trigger:** `{auto_command}`"
            
        await interaction.followup.send(msg)

    # 2. /shop-remove
    @app_commands.command(name="shop-remove", description="[Admin] Remove an item from the global shop.")
    @app_commands.describe(item_name="Exact name of the item to remove")
    @app_commands.default_permissions(administrator=True)
    async def shop_remove(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=True)
        async with self.bot.db_pool.acquire() as conn:
            result = await conn.execute("DELETE FROM global_shop WHERE LOWER(item_name) = LOWER($1);", item_name)
            
        if result == "DELETE 0":
            await interaction.followup.send(f"❌ Could not find `{item_name}` in the shop.", ephemeral=True)
        else:
            await interaction.followup.send(f"🗑️ **Shop Updated:** Successfully removed `{item_name}`.")

    # 3. /eco-leaderboard
    @app_commands.command(name="eco-leaderboard", description="View the top 10 richest players globally.")
    async def eco_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self.bot.db_pool.acquire() as conn:
            top_users = await conn.fetch("SELECT user_id, (wallet + bank) as net_worth FROM users ORDER BY net_worth DESC LIMIT 10;")
            
        if not top_users:
            return await interaction.followup.send("❌ No users found in the database.")
            
        embed = discord.Embed(title="🏆 Global Economy Leaderboard", color=discord.Color.gold())
        
        for index, row in enumerate(top_users, start=1):
            user = self.bot.get_user(int(row['user_id']))
            username = user.display_name if user else f"Unknown User ({row['user_id']})"
            embed.add_field(name=f"#{index} - {username}", value=f"**{row['net_worth']:,}** 🪙 Net Worth", inline=False)
            
        await interaction.followup.send(embed=embed)

    # 4. /eco-search
    @app_commands.command(name="eco-search", description="[Admin] Deep scan a user's economy profile and limits.")
    @app_commands.describe(user="The player to scan")
    @app_commands.default_permissions(administrator=True)
    async def eco_search(self, interaction: discord.Interaction, user: discord.User):
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", str(user.id))
            inventory = await conn.fetch("SELECT item_name, quantity FROM inventories WHERE user_id = $1", str(user.id))
            
        embed = discord.Embed(title=f"🔍 Audit Log: {user.display_name}", color=discord.Color.dark_grey())
        embed.add_field(name="Wallet", value=f"{row['wallet']:,}", inline=True)
        embed.add_field(name="Bank", value=f"{row['bank']:,} / {row['bank_limit']:,}", inline=True)
        embed.add_field(name="Status", value=f"{'🧊 Frozen' if row['is_frozen'] else '✅ Active'}", inline=True)
        embed.add_field(name="Blacklisted", value=f"{'💀 YES' if row['is_blacklisted'] else '❌ NO'}", inline=True)
        
        inv_text = "\n".join([f"• {item['quantity']}x {item['item_name']}" for item in inventory]) if inventory else "Empty"
        embed.add_field(name="Inventory", value=inv_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 5. /eco-freeze
    @app_commands.command(name="eco-freeze", description="[Admin] Freeze a user's account, preventing money movement.")
    @app_commands.describe(user="The player to freeze")
    @app_commands.default_permissions(administrator=True)
    async def eco_freeze(self, interaction: discord.Interaction, user: discord.User):
        await self.ensure_user(user.id)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_frozen = TRUE WHERE user_id = $1", str(user.id))
        await interaction.response.send_message(f"🧊 **Account Frozen:** {user.mention} can no longer use economy commands.", ephemeral=True)

    # 6. /eco-unfreeze
    @app_commands.command(name="eco-unfreeze", description="[Admin] Unfreeze a user's account.")
    @app_commands.describe(user="The player to unfreeze")
    @app_commands.default_permissions(administrator=True)
    async def eco_unfreeze(self, interaction: discord.Interaction, user: discord.User):
        await self.ensure_user(user.id)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_frozen = FALSE WHERE user_id = $1", str(user.id))
        await interaction.response.send_message(f"🔥 **Account Unfrozen:** {user.mention} is free to use the economy again.", ephemeral=True)

    # 7. /bank-limit
    @app_commands.command(name="bank-limit", description="[Admin] Adjust the maximum bank capacity for a user.")
    @app_commands.describe(user="Target player", limit="New maximum bank size")
    @app_commands.default_permissions(administrator=True)
    async def bank_limit(self, interaction: discord.Interaction, user: discord.User, limit: int):
        if limit < 0:
            return await interaction.response.send_message("❌ Limit cannot be negative.", ephemeral=True)
            
        await self.ensure_user(user.id)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET bank_limit = $1 WHERE user_id = $2", limit, str(user.id))
        await interaction.response.send_message(f"🏦 **Limit Adjusted:** {user.mention}'s bank capacity is now **{limit:,}**.", ephemeral=True)

    # 8. /item-give
    @app_commands.command(name="item-give", description="[Admin] Manually inject a shop item into a user's inventory.")
    @app_commands.describe(user="Target player", item_name="Exact name of the item", quantity="Amount to give")
    @app_commands.default_permissions(administrator=True)
    async def item_give(self, interaction: discord.Interaction, user: discord.User, item_name: str, quantity: int = 1):
        if quantity <= 0:
            return await interaction.response.send_message("❌ Quantity must be positive.", ephemeral=True)
            
        await self.ensure_user(user.id)
        await interaction.response.defer(ephemeral=True)
        
        async with self.bot.db_pool.acquire() as conn:
            has_item = await conn.fetchval("SELECT id FROM inventories WHERE user_id = $1 AND LOWER(item_name) = LOWER($2)", str(user.id), item_name)
            
            if has_item:
                await conn.execute("UPDATE inventories SET quantity = quantity + $1 WHERE id = $2", quantity, has_item)
            else:
                await conn.execute("INSERT INTO inventories (user_id, item_name, quantity) VALUES ($1, $2, $3)", str(user.id), item_name, quantity)
                
        await interaction.followup.send(f"📦 Successfully gave **{quantity}x {item_name}** to {user.mention}.")

    # 9. /eco-wipe
    @app_commands.command(name="eco-wipe", description="[Admin] Completely erase a user's wallet, bank, and inventory to 0.")
    @app_commands.describe(user="The player to wipe")
    @app_commands.default_permissions(administrator=True)
    async def eco_wipe(self, interaction: discord.Interaction, user: discord.User):
        await self.ensure_user(user.id)
        await interaction.response.defer(ephemeral=True)
        
        async with self.bot.db_pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE users SET wallet = 0, bank = 0 WHERE user_id = $1", str(user.id))
                await conn.execute("DELETE FROM inventories WHERE user_id = $1", str(user.id))
                
        await interaction.followup.send(f"☢️ **WIPE COMPLETE:** {user.mention}'s economy profile has been entirely neutralized.")

    # 10. /eco-blacklist
    @app_commands.command(name="eco-blacklist", description="[Admin] Permanently ban a user from the economy system.")
    @app_commands.describe(user="The player to blacklist")
    @app_commands.default_permissions(administrator=True)
    async def eco_blacklist(self, interaction: discord.Interaction, user: discord.User):
        await self.ensure_user(user.id)
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_blacklisted = TRUE WHERE user_id = $1", str(user.id))
        await interaction.response.send_message(f"💀 **Blacklisted:** {user.mention} is now permanently barred from economy access.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Staff(bot))
