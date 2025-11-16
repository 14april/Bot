import discord
from discord.ext import commands
from discord import app_commands

import database
import localization # Import file localization mới

class LanguageCommandCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="language", description="Thay đổi ngôn ngữ hiển thị của bot.")
    @app_commands.describe(language="Chọn ngôn ngữ bạn muốn dùng")
    @app_commands.choices(language=[
        app_commands.Choice(name="Tiếng Việt 🇻🇳", value="vi"),
        app_commands.Choice(name="English 🇬🇧", value="en"),
    ])
    async def language(self, interaction: discord.Interaction, language: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        data = await database.get_user_data(user_id)
        if data is None:
            # Lỗi DB, gửi tạm 1 ngôn ngữ
            await interaction.followup.send("❌ Database error. Please try again.", ephemeral=True)
            return
        
        # Lấy ngôn ngữ mới
        new_lang = language.value
        data['language'] = new_lang
        
        await database.save_user_data(user_id, data)
        
        # Trả lời bằng ngôn ngữ MỚI mà người dùng vừa chọn
        await interaction.followup.send(
            localization.get_string(new_lang, 'lang_changed_success'),
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LanguageCommandCog(bot))
    print("✅ Cog 'language_command' đã được tải.")
