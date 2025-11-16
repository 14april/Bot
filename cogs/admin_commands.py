import discord
from discord.ext import commands
from discord import app_commands

import config
import database
import localization # <-- THÊM NÀY

class AdminCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_lang(self, interaction: discord.Interaction):
        """Helper để lấy ngôn ngữ của user"""
        data = await database.get_user_data(interaction.user.id)
        if data is None:
            return 'vi'
        return data.get('language', 'vi')

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
        user_lang = await self.get_lang(interaction) # <-- LẤY NGÔN NGỮ

        if amount <= 0:
            return await interaction.followup.send(localization.get_string(user_lang, 'admin_buff_gt_zero'), ephemeral=True) # <-- SỬA

        data = await database.get_user_data(target_member.id)
        currency_key = currency_type.value
        data[currency_key] = data.get(currency_key, 0) + amount
        await database.save_user_data(target_member.id, data)
        # <-- SỬA -->
        await interaction.followup.send(
            localization.get_string(
                user_lang, 
                'admin_buff_success', 
                amount=amount, 
                currency_key=currency_key.capitalize(), 
                member_mention=target_member.mention
            ), 
            ephemeral=True
        )

    @buff_command.error
    async def buff_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        user_lang = await self.get_lang(interaction) # <-- LẤY NGÔN NGỮ
        if isinstance(error, commands.NotOwner):
            await interaction.response.send_message(localization.get_string(user_lang, 'admin_not_owner'), ephemeral=True) # <-- SỬA
        else:
            await interaction.response.send_message(localization.get_string(user_lang, 'generic_error', error=error), ephemeral=True) # <-- SỬA

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommandsCog(bot))
    print("✅ Cog 'admin_commands' đã được tải.")
