import discord
from discord.ext import commands
from discord import app_commands

import config
import database
import localization # <-- THÊM NÀY
from cogs.level_system import get_user_rank_key 

class LeaderboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    leaderboard_group = app_commands.Group(name="leaderboard", description="Xem bảng xếp hạng theo XP")

    async def get_lang(self, interaction: discord.Interaction):
        """Helper để lấy ngôn ngữ của user"""
        data = await database.get_user_data(interaction.user.id)
        if data is None:
            return 'vi'
        return data.get('language', 'vi')

    @leaderboard_group.command(name="hero", description="Bảng xếp hạng các Hero theo Rank")
    @app_commands.describe(rank="Chọn rank Hero để xem")
    @app_commands.choices(rank=[
        app_commands.Choice(name="Class S", value="HERO_S"),
        app_commands.Choice(name="Class A", value="HERO_A"),
        app_commands.Choice(name="Class B", value="HERO_B"),
        app_commands.Choice(name="Class C", value="HERO_C"),
    ])
    async def leaderboard_hero(self, interaction: discord.Interaction, rank: app_commands.Choice[str]):
        await interaction.response.defer()
        user_lang = await self.get_lang(interaction) # <-- LẤY NGÔN NGỮ
        
        if database.db is None:
            return await interaction.followup.send(localization.get_string(user_lang, 'lb_db_not_ready'), ephemeral=True) # <-- SỬA

        try:
            users_ref = database.db.collection(config.COLLECTION_NAME).stream()
            leaderboard_entries = []

            for user_doc in users_ref:
                user_data = user_doc.to_dict()
                if user_data.get('role_group') == 'HERO':
                    current_rank_key = get_user_rank_key(user_data)
                    if current_rank_key == rank.value:
                        leaderboard_entries.append({
                            'id': int(user_doc.id),
                            'xp': user_data.get('xp', 0),
                            'level': user_data.get('level', 0)
                        })
            
            leaderboard_entries.sort(key=lambda x: (x['level'], x['xp']), reverse=True)

            # <-- SỬA -->
            embed = discord.Embed(
                title=localization.get_string(user_lang, 'lb_hero_title', rank_name=rank.name),
                description=localization.get_string(user_lang, 'lb_hero_desc', rank_name=rank.name),
                color=discord.Color.gold()
            )

            if not leaderboard_entries:
                embed.description = localization.get_string(user_lang, 'lb_no_players') # <-- SỬA
            else:
                desc_text = ""
                for i, entry in enumerate(leaderboard_entries[:10]):
                    member = interaction.guild.get_member(entry['id'])
                    # <-- SỬA -->
                    member_name = member.mention if member else localization.get_string(user_lang, 'lb_user_id', id=entry['id'])
                    desc_text += f"**{i+1}.** {member_name} - **Lv.{entry['level']}** - **{entry['xp']:,}** XP\n"
                embed.description = desc_text
            
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"❌ Lỗi khi lấy leaderboard (hero): {e}")
            await interaction.followup.send(localization.get_string(user_lang, 'lb_query_error'), ephemeral=True) # <-- SỬA

    @leaderboard_group.command(name="monster", description="Bảng xếp hạng các Monster theo Rank")
    @app_commands.describe(rank="Chọn rank Monster để xem")
    @app_commands.choices(rank=[
        app_commands.Choice(name="God", value="M_GOD"), 
        app_commands.Choice(name="Dragon", value="M_DRAGON"),
        app_commands.Choice(name="Demon", value="M_DEMON"),
        app_commands.Choice(name="Tiger", value="M_TIGER"), 
    ])
    async def leaderboard_monster(self, interaction: discord.Interaction, rank: app_commands.Choice[str]):
        await interaction.response.defer()
        user_lang = await self.get_lang(interaction) # <-- LẤY NGÔN NGỮ

        if database.db is None:
            return await interaction.followup.send(localization.get_string(user_lang, 'lb_db_not_ready'), ephemeral=True) # <-- SỬA
            
        try:
            users_ref = database.db.collection(config.COLLECTION_NAME).stream()
            leaderboard_entries = []

            for user_doc in users_ref:
                user_data = user_doc.to_dict()
                if user_data.get('role_group') == 'MONSTER':
                    current_rank_key = get_user_rank_key(user_data)
                    if current_rank_key and rank.value in current_rank_key: 
                         leaderboard_entries.append({
                            'id': int(user_doc.id),
                            'xp': user_data.get('xp', 0),
                            'level': user_data.get('level', 0)
                        })
            
            leaderboard_entries.sort(key=lambda x: (x['level'], x['xp']), reverse=True)

            # <-- SỬA -->
            embed = discord.Embed(
                title=localization.get_string(user_lang, 'lb_monster_title', rank_name=rank.name),
                description=localization.get_string(user_lang, 'lb_monster_desc', rank_name=rank.name),
                color=discord.Color.purple()
            )

            if not leaderboard_entries:
                embed.description = localization.get_string(user_lang, 'lb_no_players') # <-- SỬA
            else:
                desc_text = ""
                for i, entry in enumerate(leaderboard_entries[:10]):
                    member = interaction.guild.get_member(entry['id'])
                    # <-- SỬA -->
                    member_name = member.mention if member else localization.get_string(user_lang, 'lb_user_id', id=entry['id'])
                    desc_text += f"**{i+1}.** {member_name} - **Lv.{entry['level']}** - **{entry['xp']:,}** XP\n"
                embed.description = desc_text
                
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"❌ Lỗi khi lấy leaderboard (monster): {e}")
            await interaction.followup.send(localization.get_string(user_lang, 'lb_query_error'), ephemeral=True) # <-- SỬA

async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
    print("✅ Cog 'leaderboard' đã được tải.")
