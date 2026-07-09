# -*- coding: utf-8 -*-
"""
CasinoForge - Staff Cog
Moderation and economy management commands
"""

import discord
from discord.ext import commands
import app_commands
import logging

logger = logging.getLogger('CasinoForge.Staff')

class Staff(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ensure_user(self, user_id: int):
        """Ensure user exists in database."""
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                str(user_id)
            )

    @app_commands.command(name="eco-add", description="[Admin] Add coins to a user's wallet.")
    @app_commands.describe(user="User to add coins to", amount="Amount to add")
    @app_commands.default_permissions(administrator=True)
    async def eco_add(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Admin: Add coins to a user."""
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
            return
        
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET wallet = wallet + $1 WHERE user_id = $2",
                amount,
                str(user.id)
            )
        
        await interaction.response.send_message(
            f"✅ Added **{amount:,}** coins to {user.mention}'s wallet."
        )

    @app_commands.command(name="eco-remove", description="[Admin] Remove coins from a user's wallet.")
    @app_commands.describe(user="User to remove coins from", amount="Amount to remove")
    @app_commands.default_permissions(administrator=True)
    async def eco_remove(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Admin: Remove coins from a user."""
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
            return
        
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            balance = await conn.fetchval(
                "SELECT wallet FROM users WHERE user_id = $1",
                str(user.id)
            )
            
            if balance < amount:
                await interaction.response.send_message(
                    f"❌ {user.mention} only has **{balance:,}** coins.",
                    ephemeral=True
                )
                return
            
            await conn.execute(
                "UPDATE users SET wallet = wallet - $1 WHERE user_id = $2",
                amount,
                str(user.id)
            )
        
        await interaction.response.send_message(
            f"✅ Removed **{amount:,}** coins from {user.mention}'s wallet."
        )

    @app_commands.command(name="eco-freeze", description="[Admin] Freeze a user's account (blocks transactions).")
    @app_commands.describe(user="User to freeze")
    @app_commands.default_permissions(administrator=True)
    async def eco_freeze(self, interaction: discord.Interaction, user: discord.User):
        """Admin: Freeze a user's account."""
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_frozen = TRUE WHERE user_id = $1",
                str(user.id)
            )
        
        await interaction.response.send_message(
            f"❄️ Frozen {user.mention}'s account. They can no longer perform transactions."
        )

    @app_commands.command(name="eco-unfreeze", description="[Admin] Unfreeze a user's account.")
    @app_commands.describe(user="User to unfreeze")
    @app_commands.default_permissions(administrator=True)
    async def eco_unfreeze(self, interaction: discord.Interaction, user: discord.User):
        """Admin: Unfreeze a user's account."""
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_frozen = FALSE WHERE user_id = $1",
                str(user.id)
            )
        
        await interaction.response.send_message(
            f"✅ Unfrozen {user.mention}'s account."
        )

    @app_commands.command(name="eco-wipe", description="[Admin] Completely wipe a user's balance.")
    @app_commands.describe(user="User to wipe")
    @app_commands.default_permissions(administrator=True)
    async def eco_wipe(self, interaction: discord.Interaction, user: discord.User):
        """Admin: Wipe all coins from a user."""
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET wallet = 0, bank = 0 WHERE user_id = $1",
                str(user.id)
            )
        
        await interaction.response.send_message(
            f"💀 Wiped {user.mention}'s entire balance."
        )

    @app_commands.command(name="eco-search", description="[Admin] View a user's complete economy profile.")
    @app_commands.describe(user="User to search")
    @app_commands.default_permissions(administrator=True)
    async def eco_search(self, interaction: discord.Interaction, user: discord.User):
        """Admin: View user's economy profile."""
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT wallet, bank, bank_limit, is_frozen, is_blacklisted FROM users WHERE user_id = $1",
                str(user.id)
            )
        
        if row is None:
            await interaction.response.send_message("❌ User not found.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🔍 Economy Profile: {user.display_name}",
            color=discord.Color.dark_grey()
        )
        embed.add_field(name="Wallet", value=f"**{row['wallet']:,}** coins", inline=True)
        embed.add_field(name="Bank", value=f"**{row['bank']:,}** / **{row['bank_limit']:,}**", inline=True)
        embed.add_field(name="Total", value=f"**{row['wallet'] + row['bank']:,}** coins", inline=True)
        embed.add_field(name="Status", value=f"Frozen: {row['is_frozen']}\nBlacklisted: {row['is_blacklisted']}", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bank-limit", description="[Admin] Adjust a user's bank capacity.")
    @app_commands.describe(user="User to modify", limit="New bank limit")
    @app_commands.default_permissions(administrator=True)
    async def bank_limit(self, interaction: discord.Interaction, user: discord.User, limit: int):
        """Admin: Set user's bank limit."""
        if limit < 0:
            await interaction.response.send_message("❌ Bank limit must be non-negative.", ephemeral=True)
            return
        
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET bank_limit = $1 WHERE user_id = $2",
                limit,
                str(user.id)
            )
        
        await interaction.response.send_message(
            f"🏦 Set {user.mention}'s bank limit to **{limit:,}** coins."
        )

    @app_commands.command(name="blacklist", description="[Admin] Blacklist a user (permanent account ban).")
    @app_commands.describe(user="User to blacklist")
    @app_commands.default_permissions(administrator=True)
    async def blacklist(self, interaction: discord.Interaction, user: discord.User):
        """Admin: Blacklist a user."""
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_blacklisted = TRUE WHERE user_id = $1",
                str(user.id)
            )
        
        await interaction.response.send_message(
            f"🚫 Blacklisted {user.mention} from the economy system."
        )

    @app_commands.command(name="unblacklist", description="[Admin] Remove a user from blacklist.")
    @app_commands.describe(user="User to unblacklist")
    @app_commands.default_permissions(administrator=True)
    async def unblacklist(self, interaction: discord.Interaction, user: discord.User):
        """Admin: Unblacklist a user."""
        await self.ensure_user(user.id)
        
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_blacklisted = FALSE WHERE user_id = $1",
                str(user.id)
            )
        
        await interaction.response.send_message(
            f"✅ Removed {user.mention} from the blacklist."
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Staff(bot))
    logger.info("Staff cog loaded")
