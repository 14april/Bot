import discord
from discord.ext import commands
from discord import app_commands

import config
import database

class AdminCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="buff", description="[OWNER ONLY] Thêm Fund/Coupon cho người chơi.")
    @commands.is_owner()
    @app_commands.describe(
        target_member="Người chơi cần buff.",
        currency_type="Loại tiền muốn thêm.",
        amount="Số lượng muốn thêm."
    )
    @app_commands.choices(currency_type=[
        app_commands.Choice(name="💰 Fund", value="fund"),
        app_commands.Choice(name="🎟️ Coupon", value="coupon"),
    ])
    async def buff_command(self, interaction: discord.Interaction, target_member: discord.Member, currency_type: app_commands.Choice[str], amount: int):
        await interaction.response.defer(ephemeral=True)
        if amount <= 0:
            return await interaction.followup.send("❌ Số tiền phải lớn hơn 0.", ephemeral=True)

        data = await database.get_user_data(target_member.id)
        currency_key = currency_type.value
        data[currency_key] = data.get(currency_key, 0) + amount
        await database.save_user_data(target_member.id, data)
        await interaction.followup.send(f"✅ Đã thêm **{amount:,}** {currency_key.capitalize()} cho {target_member.mention}.", ephemeral=True)

    @buff_command.error
    async def buff_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, commands.NotOwner):
            await interaction.response.send_message("⛔ Lệnh này chỉ dành cho Owner của Bot.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Đã xảy ra lỗi: {error}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommandsCog(bot))
    print("✅ Cog 'admin_commands' đã được tải.")
