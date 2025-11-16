import discord
from discord.ext import commands
from datetime import datetime, timedelta
import random

# Import các file tiện ích
import config
import database
import localization # <-- THÊM NÀY

# --- CÁC HÀM LOGIC CỐT LÕI (Từ file cũ) ---
def get_required_xp(level):
    return int(config.BASE_XP_TO_LEVEL * (level + 1) ** config.XP_SCALING)

def get_current_rank_role(data):
    # (Hàm này không đổi)
    group = data.get('role_group')
    level = data.get('level', 0)
    if not group or level == 0: return None
    tiers = config.LEVEL_TIERS.get(group)
    if not tiers: return None
    current_rank_key = None
    for lvl in sorted(tiers.keys()):
        if level >= lvl:
            current_rank_key = tiers[lvl]
        else:
            break
    return config.ROLE_IDS.get(current_rank_key) if current_rank_key else None

def get_user_rank_key(data):
    # (Hàm này không đổi)
    group = data.get('role_group')
    level = data.get('level', 0)
    if not group or level == 0: return None
    tiers = config.LEVEL_TIERS.get(group)
    if not tiers: return None
    current_rank_key = None
    for lvl in sorted(tiers.keys()):
        if level >= lvl:
            current_rank_key = tiers[lvl]
        else:
            break
    return current_rank_key

async def update_user_level_and_roles(member, data):
    guild = member.guild
    new_level = data['level']
    level_up_occurred = False
    
    user_lang = data.get('language', 'vi') # <-- LẤY NGÔN NGỮ

    while data.get('xp', 0) >= get_required_xp(new_level):
        data['xp'] -= get_required_xp(new_level)
        new_level += 1
        level_up_occurred = True
        
        reward_fund = random.randint(10_000_000_000, 999_000_000_000)
        reward_coupon = random.randint(10_000_000_000, 999_000_000_000)
        
        data['fund'] = data.get('fund', 0) + reward_fund
        data['coupon'] = data.get('coupon', 0) + reward_coupon
        
        try:
            # <-- SỬA (Gửi DM đa ngôn ngữ) -->
            await member.send(
                localization.get_string(
                    user_lang,
                    'level_up_dm',
                    mention=member.mention,
                    new_level=new_level,
                    reward_fund=reward_fund,
                    fund_emoji=config.ROLE_IDS['FUND_EMOJI'],
                    reward_coupon=reward_coupon,
                    coupon_emoji=config.ROLE_IDS['COUPON_EMOJI']
                )
            )
        except discord.Forbidden:
            pass

    if level_up_occurred:
        data['level'] = new_level
        await database.save_user_data(member.id, data) 

    if data.get('role_group'):
        new_role_id = get_current_rank_role(data)
        if new_role_id:
            new_role = guild.get_role(new_role_id)
            if not new_role: return

            group_prefix = 'HERO' if data['role_group'] == 'HERO' else 'M_'
            all_rank_roles_ids = [id for key, id in config.ROLE_IDS.items()
                                     if key.startswith(group_prefix) and key not in ('HERO_GROUP', 'MONSTER_GROUP')]
            roles_to_remove = [r for r in member.roles 
                                 if r.id in all_rank_roles_ids and r.id != new_role.id]

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Auto Role: Gỡ Rank cũ")
            if new_role not in member.roles:
                await member.add_roles(new_role, reason="Auto Role: Cấp Rank mới")
                try:
                    # <-- SỬA (Gửi DM đa ngôn ngữ) -->
                    await member.send(localization.get_string(user_lang, 'rank_up_dm', new_role_name=new_role.name))
                except discord.Forbidden:
                    pass

# --- CLASS COG ---
class LevelSystemCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or database.db is None or not isinstance(message.channel, discord.TextChannel):
            return

        user_id = message.author.id
        data = await database.get_user_data(user_id) 
        if data is None:
            return

        last_xp = data.get('last_xp_message', datetime.min)
        if not isinstance(last_xp, datetime):
            last_xp = datetime.min 

        if datetime.now() - last_xp > timedelta(seconds=config.XP_COOLDOWN_SECONDS):
            data['xp'] = data.get('xp', 0) + random.randint(5, 15)
            data['last_xp_message'] = datetime.now()
            
            old_level = data.get('level', 0)
            await update_user_level_and_roles(message.author, data)

            if data.get('level', 0) == old_level:
                await database.save_user_data(user_id, data)

# Hàm setup
async def setup(bot: commands.Bot):
    await bot.add_cog(LevelSystemCog(bot))
    print("✅ Cog 'level_system' đã được tải.")
