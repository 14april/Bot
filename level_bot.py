import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
import random
import json
import asyncio
from firebase_admin import firestore

import discord
from discord import app_commands
from discord.ext import commands

# --- FIREBASE IMPORTS ---
import firebase_admin
from firebase_admin import credentials, firestore
# ------------------------

# ==============================================================================
# CẤU HÌNH LƯU TRỮ DỮ LIỆU VÀ ID
# ==============================================================================

# COLLECTION_NAME là nơi lưu trữ data người dùng trong Firestore
COLLECTION_NAME = 'discord_bot_users'
# COLLECTION_FOR_CONFIG là nơi lưu trữ ID tin nhắn Reaction Role
CONFIG_COLLECTION = 'discord_bot_config'
CONFIG_DOC_ID = 'reaction_roles' # Document chứa cấu hình reaction role

db = None

# Cấu hình Role ID (BẠN CẦN THAY THẾ CHÚNG BẰNG ID THỰC CỦA SERVER BẠN)
ROLE_IDS = {
    # Nhóm vai trò chính (ID MẪU - CẦN THAY)
    "HERO_GROUP": 1428605131372494888, 
    "MONSTER_GROUP": 1428606008678289418,

    # Hero Ranks (ID MẪU - CẦN THAY)
    "HERO_C": 1428609299550175293,
    "HERO_B": 1428609397906477116,
    "HERO_A": 1428609426117492756,
    "HERO_S": 1428609449173454859,

    # Monster Ranks (ID MẪU - CẦN THAY)
    "M_TIGER_LOW": 1428609481549414493,
    "M_TIGER_MID": 1428609524826112121,
    "M_TIGER_HIGH": 1428609554794418267,
    "M_DEMON_LOW": 1428609624952799262,
    "M_DEMON_MID": 1428609662466527272,
    "M_DEMON_HIGH": 1428609686843953236,
    "M_DRAGON_LOW": 1428609714521903186,
    "M_DRAGON_MID": 1428655205951602759,
    "M_DRAGON_HIGH": 1428655242936975392,
    "M_GOD": 1428609742116225034,

    # Tiền tệ (Emoji/Icon ID MẪU - CẦN THAY)
    "FUND_EMOJI": "<:fund:1378705631426646016>",
    "COUPON_EMOJI": "<:coupon:1428342053548462201>",
}

# Cấu hình XP và Level
LEVEL_TIERS = {
    "HERO": {1: "HERO_C", 5: "HERO_B", 10: "HERO_A", 15: "HERO_S"},
    "MONSTER": {
        1: "M_TIGER_LOW", 3: "M_TIGER_MID", 5: "M_TIGER_HIGH",
        7: "M_DEMON_LOW", 9: "M_DEMON_MID", 11: "M_DEMON_HIGH",
        13: "M_DRAGON_LOW", 15: "M_DRAGON_MID", 17: "M_DRAGON_HIGH",
        20: "M_GOD"
    }
}
BASE_XP_TO_LEVEL = 100
XP_SCALING = 1.5

# Cooldown nhận XP khi nhắn tin
XP_COOLDOWN_SECONDS = 5

# Cấu hình Reaction Role để dễ dàng truy cập
REACTION_ROLES_CONFIG = {
    "⚔️": "HERO_GROUP", # Role ID cho Hero Group
    "👹": "MONSTER_GROUP", # Role ID cho Monster Group
}


# ====== Fake web server để Render không bị kill ======
class PingServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")

def run_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PingServer)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()


# ====== Cấu hình intents và bot ======
intents = discord.Intents.default()
# Cần các intents này cho Reaction Role và on_message
intents.members = True 
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ==============================================================================
# FIRESTORE UTILITY FUNCTIONS
# ==============================================================================

def initialize_firestore():
    """Khởi tạo Firebase Admin SDK sử dụng biến môi trường FIREBASE_CREDENTIALS."""
    global db
    if db is not None:
        return

    try:
        cred_json = os.getenv("FIREBASE_CREDENTIALS")
        if not cred_json:
            print("❌ Lỗi: Không tìm thấy biến môi trường FIREBASE_CREDENTIALS.")
            return

        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            
        db = firestore.client()
        print("✅ Đã kết nối thành công với Firestore.")

    except Exception as e:
        print(f"❌ Lỗi khởi tạo Firebase/Firestore: {e}. Vui lòng kiểm tra FIREBASE_CREDENTIALS.")
        db = None 


async def get_user_data(user_id):
    """Lấy dữ liệu người dùng từ Firestore. Nếu chưa có, trả về dữ liệu mặc định."""
    global db
    if db is None:
        initialize_firestore() 
        if db is None:
            return None 

    doc_ref = db.collection(COLLECTION_NAME).document(str(user_id))
    try:
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()

            # Xử lý các trường datetime từ Firestore Timestamp
            if data.get('last_xp_message') and isinstance(data['last_xp_message'], datetime):
                data['last_xp_message'] = data['last_xp_message'].replace(tzinfo=None)
            else:
                # Firestore Timestamp cần được chuyển thành datetime object
                if data.get('last_xp_message') and isinstance(data['last_xp_message'], firestore.client.datetime):
                    data['last_xp_message'] = data['last_xp_message'].replace(tzinfo=None)
                else:
                     data['last_xp_message'] = datetime.min

            if data.get('last_daily') and isinstance(data['last_daily'], datetime):
                data['last_daily'] = data['last_daily'].replace(tzinfo=None)
            else:
                 if data.get('last_daily') and isinstance(data['last_daily'], firestore.client.datetime):
                    data['last_daily'] = data['last_daily'].replace(tzinfo=None)
                 else:
                    data['last_daily'] = None

            return data
        else:
            # Tạo dữ liệu mặc định nếu người dùng chưa tồn tại
            default_data = {
                'xp': 0,
                'level': 0,
                'fund': 0,
                'coupon': 0,
                'role_group': None,
                'last_daily': None,
                'last_xp_message': datetime.min,
            }
            return default_data

    except Exception as e:
        print(f"❌ Lỗi khi lấy dữ liệu cho user {user_id}: {e}")
        return None


async def save_user_data(user_id, data):
    """Lưu dữ liệu người dùng vào Firestore."""
    global db
    if db is None:
        initialize_firestore() 
        if db is None:
            print(f"🛑 Không thể lưu dữ liệu cho user {user_id}. DB chưa sẵn sàng.")
            return

    doc_ref = db.collection(COLLECTION_NAME).document(str(user_id))
    data_to_save = data.copy()

    try:
        doc_ref.set(data_to_save)
    except Exception as e:
        print(f"❌ Lỗi khi lưu dữ liệu cho user {user_id}: {e}")
        db = None

async def get_reaction_message_ids():
    """Lấy Message ID và Channel ID của tin nhắn Reaction Role từ Firestore."""
    if db is None: return {}
    
    doc_ref = db.collection(CONFIG_COLLECTION).document(CONFIG_DOC_ID)
    try:
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get('messages', {})
        return {}
    except Exception as e:
        print(f"❌ Lỗi khi lấy cấu hình Reaction Role: {e}")
        return {}

async def save_reaction_message_id(guild_id, message_id, channel_id):
    """Lưu Message ID và Channel ID của tin nhắn Reaction Role vào Firestore."""
    if db is None: return
    
    doc_ref = db.collection(CONFIG_COLLECTION).document(CONFIG_DOC_ID)
    try:
        @firestore.transactional
        def update_config_transaction(transaction):
            snapshot = doc_ref.get(transaction=transaction)
            config_data = snapshot.to_dict() or {'messages': {}}
            config_data['messages'][str(guild_id)] = {
                'message_id': str(message_id),
                'channel_id': str(channel_id)
            }
            transaction.set(doc_ref, config_data)
        
        transaction = db.transaction()
        update_config_transaction(transaction)
        
    except Exception as e:
        print(f"❌ Lỗi khi lưu cấu hình Reaction Role: {e}")


# ==============================================================================
# CORE LOGIC FUNCTIONS: XP, LEVEL, ROLE
# ==============================================================================

def get_required_xp(level):
    """Tính XP cần thiết để lên level tiếp theo."""
    return int(BASE_XP_TO_LEVEL * (level + 1) ** XP_SCALING)

def get_current_rank_role(data):
    """Xác định ID Role Rank dựa trên Level và Group."""
    group = data.get('role_group')
    level = data.get('level', 0)

    if not group or level == 0:
        return None

    tiers = LEVEL_TIERS.get(group)
    if not tiers:
        return None

    current_rank_key = None
    sorted_levels = sorted(tiers.keys())
    for lvl in sorted_levels:
        if level >= lvl:
            current_rank_key = tiers[lvl]
        else:
            break

    return ROLE_IDS.get(current_rank_key) if current_rank_key else None


async def update_user_level_and_roles(member, data):
    """Kiểm tra và cập nhật Level, sau đó áp dụng Role Rank mới, và THÊM THƯỞNG ngẫu nhiên."""
    guild = member.guild
    
    new_level = data['level']
    level_up_occurred = False

    while data.get('xp', 0) >= get_required_xp(new_level):
        data['xp'] -= get_required_xp(new_level)
        new_level += 1
        level_up_occurred = True
        
        reward_fund = random.randint(50, 150)
        reward_coupon = random.randint(10, 30)
        
        data['fund'] = data.get('fund', 0) + reward_fund
        data['coupon'] = data.get('coupon', 0) + reward_coupon
        
        try:
            await member.send(
                f"🎉 Chúc mừng {member.mention}! Bạn đã thăng cấp lên **Level {new_level}**!\n"
                f"🎁 Thưởng Level Up: **+{reward_fund}** {ROLE_IDS['FUND_EMOJI']} Fund và **+{reward_coupon}** {ROLE_IDS['COUPON_EMOJI']} Coupon!"
            )
        except discord.Forbidden:
            pass

    if level_up_occurred:
        data['level'] = new_level
        await save_user_data(member.id, data)

    if data.get('role_group'):
        new_role_id = get_current_rank_role(data)
        if new_role_id:
            new_role = guild.get_role(new_role_id)
            if not new_role: return

            group_prefix = 'HERO' if data['role_group'] == 'HERO' else 'M_'
            all_rank_roles_ids = [id for key, id in ROLE_IDS.items()
                                     if key.startswith(group_prefix) and key not in ('HERO_GROUP', 'MONSTER_GROUP')]
            roles_to_remove = [r for r in member.roles 
                                 if r.id in all_rank_roles_ids and r.id != new_role.id]

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Auto Role: Gỡ Rank cũ")
            if new_role not in member.roles:
                await member.add_roles(new_role, reason="Auto Role: Cấp Rank mới")
                try:
                    await member.send(f"🌟 Bạn đã được thăng cấp Rank thành **{new_role.name}**!")
                except discord.Forbidden:
                    pass

# ==============================================================================
# DISCORD EVENTS & COMMANDS
# ==============================================================================

@bot.event
async def on_ready():
    global db
    retry_count = 0
    max_retries = 10 
    while db is None and retry_count < max_retries:
        print(f"🔄 Thử kết nối Firestore lần {retry_count + 1}...")
        initialize_firestore() 
        if db is None:
            retry_count += 1
            await asyncio.sleep(2 * retry_count) 
        else:
            break 
    if db is None:
        print("🛑 Lỗi nghiêm trọng: KHÔNG THỂ kết nối Firestore sau nhiều lần thử.")
    print(f"✅ Bot Level/Tiền tệ đã đăng nhập thành công: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Đã đồng bộ {len(synced)} lệnh slash.")
    except Exception as e:
        print(f"❌ Lỗi sync command: {e}")

@bot.event
async def on_message(message):
    if message.author.bot or db is None or not isinstance(message.channel, discord.TextChannel):
        await bot.process_commands(message)
        return

    user_id = message.author.id
    data = await get_user_data(user_id)
    if data is None:
        await bot.process_commands(message)
        return

    last_xp = data.get('last_xp_message', datetime.min)
    if not isinstance(last_xp, datetime):
        last_xp = datetime.min 

    if datetime.now() - last_xp > timedelta(seconds=XP_COOLDOWN_SECONDS):
        data['xp'] = data.get('xp', 0) + random.randint(5, 15)
        data['last_xp_message'] = datetime.now()
        
        old_level = data.get('level', 0)
        await update_user_level_and_roles(message.author, data)

        if data.get('level', 0) == old_level:
            await save_user_data(user_id, data)

    await bot.process_commands(message)

# ==============================================================================
# REACTION ROLE LOGIC
# ==============================================================================

@bot.tree.command(name="setup_roles_msg", description="[ADMIN ONLY] Thiết lập tin nhắn Reaction Role.")
@commands.has_permissions(administrator=True)
async def setup_roles_msg(interaction: discord.Interaction):
    if not ROLE_IDS.get("HERO_GROUP") or not ROLE_IDS.get("MONSTER_GROUP"):
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
        await save_reaction_message_id(interaction.guild_id, message.id, interaction.channel_id)
        await interaction.edit_original_response(content="✅ Đã thiết lập thành công! Vui lòng ghim tin nhắn này.")
    except Exception as e:
        print(f"Lỗi khi thiết lập Reaction Role: {e}")
        await interaction.edit_original_response(content="❌ Lỗi: Bot không thể gửi tin nhắn hoặc thêm reaction.")

async def handle_reaction(payload, add: bool):
    if db is None: return
    config = await get_reaction_message_ids()
    guild_config = config.get(str(payload.guild_id))
    if not guild_config or payload.message_id != int(guild_config['message_id']):
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    member = guild.get_member(payload.user_id)
    if not member or member.bot: return

    role_key = REACTION_ROLES_CONFIG.get(payload.emoji.name)
    if not role_key: return

    role_id = ROLE_IDS.get(role_key)
    role = guild.get_role(role_id) if role_id else None
    if not role: return

    user_data = await get_user_data(payload.user_id)
    if user_data is None: return

    if add:
        old_group_name = user_data.get('role_group')
        new_group_name = 'HERO' if role_key == 'HERO_GROUP' else 'MONSTER'
        if old_group_name == new_group_name: return

        if old_group_name:
            old_role_id = ROLE_IDS.get(f"{old_group_name.upper()}_GROUP")
            old_role = guild.get_role(old_role_id) if old_role_id else None
            if old_role in member.roles: await member.remove_roles(old_role)
            group_prefix = 'HERO' if old_group_name == 'HERO' else 'M_'
            all_rank_roles_ids = [v for k, v in ROLE_IDS.items() if k.startswith(group_prefix) and 'GROUP' not in k]
            roles_to_remove = [r for r in member.roles if r.id in all_rank_roles_ids]
            if roles_to_remove: await member.remove_roles(*roles_to_remove)

        if role not in member.roles: await member.add_roles(role)
        user_data['role_group'] = new_group_name
        await save_user_data(payload.user_id, user_data)
        await update_user_level_and_roles(member, user_data)
    else: # Remove reaction
        if role in member.roles:
            await member.remove_roles(role)
            group_prefix = 'HERO' if role_key == 'HERO_GROUP' else 'M_'
            all_rank_roles_ids = [v for k, v in ROLE_IDS.items() if k.startswith(group_prefix) and 'GROUP' not in k]
            roles_to_remove_rank = [r for r in member.roles if r.id in all_rank_roles_ids]
            if roles_to_remove_rank: await member.remove_roles(*roles_to_remove_rank)
            
            user_data['role_group'] = None
            await save_user_data(payload.user_id, user_data)

@bot.event
async def on_raw_reaction_add(payload):
    await handle_reaction(payload, add=True)

@bot.event
async def on_raw_reaction_remove(payload):
    await handle_reaction(payload, add=False)

# ==============================================================================
# SLASH COMMANDS
# ==============================================================================

@bot.tree.command(name="profile", description="Xem Level, XP và số tiền của bạn")
async def profile(interaction: discord.Interaction):
    data = await get_user_data(interaction.user.id)
    if data is None:
        await interaction.response.send_message("❌ Lỗi cơ sở dữ liệu.", ephemeral=True)
        return

    required_xp = get_required_xp(data.get('level', 0))
    rank_role_id = get_current_rank_role(data)
    rank_role = interaction.guild.get_role(rank_role_id) if rank_role_id else None
    
    embed = discord.Embed(title=f"👤 Hồ sơ của {interaction.user.display_name}", color=discord.Color.blue())
    embed.add_field(name="📜 Nhóm", value=data.get('role_group', 'Chưa chọn'), inline=False)
    embed.add_field(name="⭐ Level", value=f"**{data.get('level', 0)}**", inline=True)
    embed.add_field(name="🏆 Rank", value=rank_role.name if rank_role else "Chưa có", inline=True)
    embed.add_field(name="📈 XP", value=f"**{data.get('xp', 0)}** / {required_xp}", inline=False)
    embed.add_field(name="💰 Fund", value=f"**{data.get('fund', 0)}** {ROLE_IDS['FUND_EMOJI']}", inline=True)
    embed.add_field(name="🎟️ Coupon", value=f"**{data.get('coupon', 0)}** {ROLE_IDS['COUPON_EMOJI']}", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="daily", description="Điểm danh mỗi ngày để nhận thưởng (Reset 0:00)")
async def daily(interaction: discord.Interaction):
    data = await get_user_data(interaction.user.id)
    if data is None:
        await interaction.response.send_message("❌ Lỗi cơ sở dữ liệu.", ephemeral=True)
        return

    last_daily = data.get('last_daily')
    if last_daily and last_daily.date() == datetime.now().date():
        await interaction.response.send_message("⏳ Bạn đã điểm danh hôm nay rồi!", ephemeral=True)
        return

    fund_reward = random.randint(100, 300)
    coupon_reward = random.randint(50, 150)
    data['fund'] = data.get('fund', 0) + fund_reward
    data['coupon'] = data.get('coupon', 0) + coupon_reward
    data['last_daily'] = datetime.now()
    await save_user_data(interaction.user.id, data)
    await interaction.response.send_message(
        f"✅ Điểm danh thành công! Nhận được:\n"
        f"**+{fund_reward}** {ROLE_IDS['FUND_EMOJI']} & **+{coupon_reward}** {ROLE_IDS['COUPON_EMOJI']}",
        ephemeral=True
    )

@bot.tree.command(name="exchange", description="Trao đổi tiền tệ Fund 🔄 Coupon (Tỷ giá 1:1).")
@app_commands.describe(exchange_type="Loại tiền bạn muốn ĐỔI.", amount="Số lượng (tối thiểu 100).")
@app_commands.choices(exchange_type=[
    app_commands.Choice(name="💰 Fund -> Coupon", value="fund_to_coupon"),
    app_commands.Choice(name="🎟️ Coupon -> Fund", value="coupon_to_fund"),
])
async def exchange(interaction: discord.Interaction, exchange_type: app_commands.Choice[str], amount: int):
    await interaction.response.defer(ephemeral=True)
    data = await get_user_data(interaction.user.id)
    if data is None:
        return await interaction.followup.send("❌ Lỗi cơ sở dữ liệu.", ephemeral=True)
    if amount < 100:
        return await interaction.followup.send("❌ Số tiền trao đổi tối thiểu là 100.", ephemeral=True)

    source, target = ('fund', 'coupon') if exchange_type.value == "fund_to_coupon" else ('coupon', 'fund')
    if data.get(source, 0) < amount:
        return await interaction.followup.send(f"❌ Bạn không đủ {source.capitalize()}.", ephemeral=True)
    
    data[source] -= amount
    data[target] = data.get(target, 0) + amount
    await save_user_data(interaction.user.id, data)
    await interaction.followup.send(f"✅ Đã đổi **{amount:,}** {source.capitalize()} sang {target.capitalize()}.", ephemeral=True)


# ====== Lệnh /all_in (Cược 80% số tiền) ======
CURRENCY_CHOICES = [
    app_commands.Choice(name="Fund", value="fund"),
    app_commands.Choice(name="Coupon", value="coupon"),
]
@bot.tree.command(name="all_in", description="Cược 80% Fund hoặc Coupon bạn đang có (Thắng x2, Thua mất hết)")
@app_commands.describe(currency="Loại tiền tệ bạn muốn cược")
@app_commands.choices(currency=CURRENCY_CHOICES)
async def all_in(interaction: discord.Interaction, currency: app_commands.Choice[str]):
    await interaction.response.defer() 

    user_id = interaction.user.id
    data = await get_user_data(user_id)

    if data is None:
        await interaction.followup.send("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng.", ephemeral=True)
        return
    
    currency_key = currency.value 
    currency_name = currency.name 
    currency_emoji = ROLE_IDS[f"{currency_name.upper()}_EMOJI"]
    
    current_balance = data.get(currency_key, 0)
    bet_amount = int(current_balance * 0.8)

    if bet_amount <= 0:
        await interaction.followup.send(
            f"❌ Bạn không có đủ {currency_name} để cược.",
            ephemeral=True
        )
        return
    
    # --- LOGIC CƯỢC VÀ HIỆU ỨNG 777 ---
    slots = ["💎", "🍒", "🔔", "🍊", "🍋", "🍇", "🎁"]
    win = random.choice([True, False])
    
    embed = discord.Embed(
        title=f"🎲 ALL IN - Cược {currency_name}",
        description=f"{interaction.user.mention} cược **{bet_amount:,}** {currency_emoji}...",
        color=discord.Color.gold()
    )
    s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
    # Gỡ bỏ code block (`) để emoji custom hiển thị tốt hơn
    embed.add_field(name="Kết quả", value=f"**> {s1} | {s2} | {s3} <**")
    
    await interaction.followup.send(embed=embed)
    message = await interaction.original_response()

    for _ in range(3):
        await asyncio.sleep(0.75)
        s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
        embed.set_field_at(0, name="Kết quả", value=f"**> {s1} | {s2} | {s3} <**")
        await message.edit(embed=embed)
    
    await asyncio.sleep(1)

    if win:
        # Sử dụng emoji của loại tiền tệ đã cược để hiển thị chiến thắng
        win_emoji = currency_emoji
        final_slots = f"**> {win_emoji} | {win_emoji} | {win_emoji} <**"
    else:
        s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
        while s1 == s2 == s3:
            s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
        final_slots = f"**> {s1} | {s2} | {s3} <**"
    
    embed.set_field_at(0, name="Kết quả", value=final_slots)
    await message.edit(embed=embed)
    await asyncio.sleep(1.5)

    old_balance = current_balance
    
    if win:
        data[currency_key] += bet_amount 
        gain_or_loss = bet_amount
        result_text = f"🎉 **THẮNG LỚN!** Bạn đã nhân đôi số tiền cược!"
        embed.color = discord.Color.green()
    else:
        data[currency_key] -= bet_amount
        gain_or_loss = -bet_amount
        result_text = f"💀 **THUA CƯỢC!** Chúc bạn may mắn lần sau."
        embed.color = discord.Color.red()

    await save_user_data(user_id, data)

    embed.description = result_text
    embed.clear_fields()
    embed.add_field(name="Loại tiền cược", value=f"{currency_emoji} {currency_name}", inline=True)
    embed.add_field(name="Số tiền cược", value=f"**{bet_amount:,}**", inline=True)
    embed.add_field(name="Lãi/Lỗ", value=f"**{'+' if gain_or_loss >= 0 else ''}{gain_or_loss:,}**", inline=True)
    embed.add_field(name="Số dư cũ", value=f"{old_balance:,}", inline=True)
    embed.add_field(name="Số dư mới", value=f"**{data[currency_key]:,}**", inline=True)
    await message.edit(embed=embed)

@bot.tree.command(name="transfer", description="Chuyển Fund/Coupon cho người chơi khác.")
@app_commands.describe(
    recipient="Người muốn chuyển tiền cho.",
    currency_type="Loại tiền muốn chuyển.",
    amount="Số lượng (tối thiểu 100)."
)
@app_commands.choices(currency_type=[
    app_commands.Choice(name="💰 Fund", value="fund"),
    app_commands.Choice(name="🎟️ Coupon", value="coupon"),
])
async def transfer_command(interaction: discord.Interaction, recipient: discord.Member, currency_type: app_commands.Choice[str], amount: int):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id == recipient.id:
        return await interaction.followup.send("❌ Bạn không thể tự chuyển cho mình.", ephemeral=True)
    if amount < 100:
        return await interaction.followup.send("❌ Số tiền chuyển tối thiểu là 100.", ephemeral=True)

    sender_data = await get_user_data(interaction.user.id)
    currency_key = currency_type.value
    if sender_data.get(currency_key, 0) < amount:
        return await interaction.followup.send(f"❌ Bạn không đủ {currency_key.capitalize()}.", ephemeral=True)

    recipient_data = await get_user_data(recipient.id)
    sender_data[currency_key] -= amount
    recipient_data[currency_key] = recipient_data.get(currency_key, 0) + amount
    await save_user_data(interaction.user.id, sender_data)
    await save_user_data(recipient.id, recipient_data)

    await interaction.followup.send(f"✅ Đã chuyển **{amount:,}** {currency_key.capitalize()} cho {recipient.mention}.", ephemeral=True)


@bot.tree.command(name="buff", description="[OWNER ONLY] Thêm Fund/Coupon cho người chơi.")
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
async def buff_command(interaction: discord.Interaction, target_member: discord.Member, currency_type: app_commands.Choice[str], amount: int):
    await interaction.response.defer(ephemeral=True)
    if amount <= 0:
        return await interaction.followup.send("❌ Số tiền phải lớn hơn 0.", ephemeral=True)

    data = await get_user_data(target_member.id)
    currency_key = currency_type.value
    data[currency_key] = data.get(currency_key, 0) + amount
    await save_user_data(target_member.id, data)
    await interaction.followup.send(f"✅ Đã thêm **{amount:,}** {currency_key.capitalize()} cho {target_member.mention}.", ephemeral=True)

@buff_command.error
async def buff_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, commands.NotOwner):
        await interaction.response.send_message("⛔ Lệnh này chỉ dành cho Owner của Bot.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Đã xảy ra lỗi: {error}", ephemeral=True)

# ====== Chạy bot ======
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("⚠️ Chưa có biến môi trường DISCORD_TOKEN!")
else:
    bot.run(TOKEN)

