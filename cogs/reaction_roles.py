import discord
from discord.ext import commands
from discord import app_commands

import config
import database
from cogs.level_system import update_user_level_and_roles # Import hàm helper

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup_roles_msg", description="[ADMIN ONLY] Thiết lập tin nhắn Reaction Role.")
    @commands.has_permissions(administrator=True)
    async def setup_roles_msg(self, interaction: discord.Interaction):
        if not config.ROLE_IDS.get("HERO_GROUP") or not config.ROLE_IDS.get("MONSTER_GROUP"):
            await interaction.response.send_message("❌ Lỗi cấu hình: Vui lòng thay ID mẫu trong ROLE_IDS.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚔️ CHỌN PHE CỦA BẠN 👹",
            description="Bấm vào biểu tượng để chọn nhóm vai trò:\n\n"
                        "**🦸‍♂️ Hero:** Bấm **⚔️**\n"
                        "**👾 Monster:** Bấm **👹**\n\n"
                        "**Cách đổi/hủy:** Bỏ reaction cũ và chọn reaction mới. Việc này sẽ **GIỮ NGUYÊN** Level và XP.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message("Đang thiết lập...", ephemeral=True)
        try:
            message = await interaction.channel.send(embed=embed)
            await message.add_reaction("⚔️")
            await message.add_reaction("👹")
            await database.save_reaction_message_id(interaction.guild_id, message.id, interaction.channel_id)
            await interaction.edit_original_response(content="✅ Đã thiết lập thành công! Vui lòng ghim tin nhắn này.")
        except Exception as e:
            print(f"Lỗi khi thiết lập Reaction Role: {e}")
            await interaction.edit_original_response(content="❌ Lỗi: Bot không thể gửi tin nhắn hoặc thêm reaction.")

    # Hàm helper được chuyển thành phương thức của class
    async def handle_reaction(self, payload: discord.RawReactionActionEvent, add: bool):
        if database.db is None: return
        config_data = await database.get_reaction_message_ids()
        guild_config = config_data.get(str(payload.guild_id))
        if not guild_config or payload.message_id != int(guild_config['message_id']):
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        role_key = config.REACTION_ROLES_CONFIG.get(payload.emoji.name)
        if not role_key: return

        role_id = config.ROLE_IDS.get(role_key)
        role = guild.get_role(role_id) if role_id else None
        if not role: return

        user_data = await database.get_user_data(payload.user_id)
        if user_data is None: return

        if add:
            old_group_name = user_data.get('role_group')
            new_group_name = 'HERO' if role_key == 'HERO_GROUP' else 'MONSTER'
            if old_group_name == new_group_name: return

            if old_group_name:
                old_role_id = config.ROLE_IDS.get(f"{old_group_name.upper()}_GROUP")
                old_role = guild.get_role(old_role_id) if old_role_id else None
                if old_role in member.roles: await member.remove_roles(old_role)
                group_prefix = 'HERO' if old_group_name == 'HERO' else 'M_'
                all_rank_roles_ids = [v for k, v in config.ROLE_IDS.items() if k.startswith(group_prefix) and 'GROUP' not in k]
                roles_to_remove = [r for r in member.roles if r.id in all_rank_roles_ids]
                if roles_to_remove: await member.remove_roles(*roles_to_remove)

            if role not in member.roles: await member.add_roles(role)
            user_data['role_group'] = new_group_name
            await database.save_user_data(payload.user_id, user_data)
            await update_user_level_and_roles(member, user_data) # Dùng helper
        else: # Remove reaction
            if role in member.roles:
                await member.remove_roles(role)
                group_prefix = 'HERO' if role_key == 'HERO_GROUP' else 'M_'
                all_rank_roles_ids = [v for k, v in config.ROLE_IDS.items() if k.startswith(group_prefix) and 'GROUP' not in k]
                roles_to_remove_rank = [r for r in member.roles if r.id in all_rank_roles_ids]
                if roles_to_remove_rank: await member.remove_roles(*roles_to_remove_rank)
                
                user_data['role_group'] = None
                await database.save_user_data(payload.user_id, user_data)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.handle_reaction(payload, add=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.handle_reaction(payload, add=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRolesCog(bot))
    print("✅ Cog 'reaction_roles' đã được tải.")
