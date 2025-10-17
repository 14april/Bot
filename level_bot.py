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

    # Chuẩn bị dữ liệu để lưu
    data_to_save = data.copy()

    # Xử lý datetime.min: Nếu là giá trị mặc định, chuyển thành Server Timestamp lần đầu (hoặc giữ nguyên nếu đã có)
    if data_to_save.get('last_xp_message') == datetime.min:
        data_to_save['last_xp_message'] = firestore.SERVER_TIMESTAMP
        
    if data_to_save.get('last_daily') == datetime.min:
        data_to_save['last_daily'] = firestore.SERVER_TIMESTAMP


    # FIX: Đã loại bỏ hoàn toàn logic chuyển đổi datetime gây lỗi ở đây (dòng 208 và 211 cũ).
    # Các đối tượng datetime tiêu chuẩn sẽ được Firestore tự động xử lý.
    # Logic cũ gây lỗi:
    # if data_to_save.get('last_xp_message') and isinstance(data_to_save['last_xp_message'], datetime):
    #     data_to_save['last_xp_message'] = datetime(...) # Dòng này gây lỗi
    # if data_to_save.get('last_daily') and isinstance(data_to_save['last_daily'], datetime):
    #     data_to_save['last_daily'] = datetime(...) # Dòng này gây lỗi

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
        # Sử dụng Transactions để đảm bảo cập nhật an toàn
        @firestore.transactional
        def update_config_transaction(transaction):
            snapshot = doc_ref.get(transaction=transaction)
            
            # Lấy data cũ hoặc khởi tạo nếu chưa có
            config_data = snapshot.to_dict() or {'messages': {}}
            
            # Cấu trúc: messages: {guild_id: {message_id: message_id, channel_id: channel_id}}
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
    
    # 1. Kiểm tra Level Up
    new_level = data['level']
    max_level_hero = max(LEVEL_TIERS['HERO'].keys()) if LEVEL_TIERS['HERO'] else 0
    max_level_monster = max(LEVEL_TIERS['MONSTER'].keys()) if LEVEL_TIERS['MONSTER'] else 0
    level_up_occurred = False

    while data['xp'] >= get_required_xp(new_level):
        # Kiểm tra giới hạn level cho nhóm hiện tại
        if (data['role_group'] == 'HERO' and new_level >= max_level_hero) or \
           (data['role_group'] == 'MONSTER' and new_level >= max_level_monster):
            # Đã đạt max level, thoát vòng lặp
            break 

        data['xp'] -= get_required_xp(new_level)
        new_level += 1
        level_up_occurred = True
        
        # --- THÊM THƯỞNG NGẪU NHIÊN KHI LÊN CẤP ---
        reward_fund = random.randint(50, 150)
        reward_coupon = random.randint(10, 30)
        
        data['fund'] += reward_fund
        data['coupon'] += reward_coupon
        # ----------------------------------------
        
        try:
            await member.send(
                f"🎉 Chúc mừng {member.mention}! Bạn đã thăng cấp lên **Level {new_level}**!\n"
                f"🎁 Thưởng Level Up: **+{reward_fund}** {ROLE_IDS['FUND_EMOJI']} Fund và **+{reward_coupon}** {ROLE_IDS['COUPON_EMOJI']} Coupon!"
            )
        except discord.Forbidden:
            pass

    if level_up_occurred:
        data['level'] = new_level
        # Lưu lại vì Level, XP và Tiền tệ đã thay đổi
        await save_user_data(member.id, data)

    # 2. Xử lý Auto Role Rank (Logic này đã TỐT, đảm bảo gỡ Role Rank cũ)
    if data['role_group']:
        new_role_id = get_current_rank_role(data)

        if new_role_id:
            new_role = guild.get_role(new_role_id)
            if not new_role:
                return

            # Xác định prefix của Rank Role để gỡ các Rank cũ
            group_prefix = 'HERO' if data['role_group'] == 'HERO' else 'M_' 
            
            # Lấy tất cả Rank Role ID của nhóm hiện tại
            all_rank_roles_ids = [id for key, id in ROLE_IDS.items()
                                     if key.startswith(group_prefix) and key not in ('HERO_GROUP', 'MONSTER_GROUP')]
            
            # Lọc ra các Role cũ cần gỡ (là Role Rank của nhóm đó VÀ không phải Rank mới)
            roles_to_remove = [r for r in member.roles 
                                 if r.id in all_rank_roles_ids and r.id != new_role.id]

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Auto Role: Gỡ Rank cũ")

            if new_role and new_role not in member.roles:
                await member.add_roles(new_role, reason="Auto Role: Cấp Rank mới")
                try:
                    await member.send(f"🌟 Bạn đã được thăng cấp Rank thành **{new_role.name}**!")
                except discord.Forbidden:
                    pass

# ==============================================================================
# DISCORD EVENTS & COMMANDS
# ==============================================================================

# ====== Khi bot sẵn sàng ======
@bot.event
async def on_ready():
    global db
    retry_count = 0
    max_retries = 10 

    # --- Đảm bảo DB được kết nối trước khi tiếp tục ---
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
    # -----------------------------------------------------------------------

    print(f"✅ Bot Level/Tiền tệ đã đăng nhập thành công: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Đã đồng bộ {len(synced)} lệnh slash.")
    except Exception as e:
        print(f"❌ Lỗi sync command: {e}")


# ====== Lắng nghe tin nhắn để tính XP ======
@bot.event
async def on_message(message):
    if message.author.bot or db is None:
        await bot.process_commands(message)
        return

    if not isinstance(message.channel, discord.TextChannel):
        await bot.process_commands(message)
        return

    user_id = message.author.id
    data = await get_user_data(user_id)
    if data is None:
        await bot.process_commands(message)
        return

    # Giới hạn XP: chỉ nhận XP sau XP_COOLDOWN_SECONDS giây
    MIN_XP_COOLDOWN = timedelta(seconds=XP_COOLDOWN_SECONDS)
    last_xp = data.get('last_xp_message', datetime.min)

    if not isinstance(last_xp, datetime):
         # Cần xử lý lại nếu last_xp không phải là datetime (ví dụ: bị lưu thành timestamp)
        last_xp = datetime.min 

    time_since_last_msg = datetime.now() - last_xp

    if time_since_last_msg > MIN_XP_COOLDOWN:
        xp_gain = random.randint(5, 15)
        data['xp'] += xp_gain
        data['last_xp_message'] = datetime.now()

        # Cập nhật Level và Role (hàm này sẽ gọi save_user_data nếu level thay đổi)
        await update_user_level_and_roles(message.author, data)

        # Nếu không level up, vẫn cần lưu lại XP và last_xp_message
        current_db_data = await get_user_data(user_id)
        if current_db_data and data.get('level', 0) == current_db_data.get('level', 0):
             # Chỉ lưu lại nếu không có thay đổi level (để tránh race condition)
            await save_user_data(user_id, data)

    await bot.process_commands(message)


# ==============================================================================
# REACTION ROLE LOGIC (NEW)
# ==============================================================================

@bot.tree.command(name="setup_roles_msg", description="[ADMIN ONLY] Thiết lập tin nhắn Reaction Role.")
@commands.has_permissions(administrator=True)
async def setup_roles_msg(interaction: discord.Interaction):
    # Lấy ID của các Role Group chính
    HERO_ROLE_ID = ROLE_IDS["HERO_GROUP"]
    MONSTER_ROLE_ID = ROLE_IDS["MONSTER_GROUP"]
    
    # Kiểm tra xem các Role đã được định nghĩa chưa
    if not HERO_ROLE_ID or not MONSTER_ROLE_ID:
        await interaction.response.send_message(
            "❌ Lỗi cấu hình: Vui lòng thay thế ID mẫu trong **ROLE_IDS** bằng ID Hero Group và Monster Group thực tế của bạn.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="⚔️ CHỌN PHE CỦA BẠN 👹", 
        description=(
            "Vui lòng bấm vào biểu tượng cảm xúc để chọn nhóm vai trò chính:\n\n"
            "**🦸‍♂️ Hero:** Bấm **⚔️** để nhận Role Hero.\n"
            "**👾 Monster:** Bấm **👹** để nhận Role Monster.\n\n"
            "**Cách đổi/hủy:** Bấm lại vào Reaction đang chọn để hủy. Sau đó bấm vào Reaction khác để đổi phe. Việc này sẽ reset Rank của nhóm cũ về 0."
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Chọn phe sẽ kích hoạt hệ thống Level & Rank của bot.")

    # Gửi tin nhắn và thêm Reactions
    await interaction.response.send_message("Đang thiết lập tin nhắn...", ephemeral=True)
    
    try:
        # Gửi tin nhắn vào kênh hiện tại
        message = await interaction.channel.send(embed=embed)
        await message.add_reaction("⚔️")
        await message.add_reaction("👹")
        
        # LƯU MESSAGE ID VÀ CHANNEL ID vào Firestore
        await save_reaction_message_id(interaction.guild_id, message.id, interaction.channel_id)
        
        await interaction.edit_original_response(
            content=f"✅ Đã thiết lập tin nhắn Reaction Role thành công! Vui lòng pin (ghim) tin nhắn này."
        )

    except Exception as e:
        print(f"Lỗi khi thiết lập Reaction Role: {e}")
        await interaction.edit_original_response(
            content="❌ Lỗi: Bot không thể gửi tin nhắn hoặc thêm reactions (kiểm tra quyền)."
        )

# Xử lý khi người dùng BẤM Reaction (Reaction Add)
@bot.event
async def on_raw_reaction_add(payload):
    # Bỏ qua nếu Reaction là của bot hoặc nếu DB chưa sẵn sàng
    if payload.member is None or payload.member.bot or db is None:
        return

    # Lấy thông tin Message ID của tin nhắn Reaction Role đã lưu
    config = await get_reaction_message_ids()
    guild_config = config.get(str(payload.guild_id))

    if not guild_config or payload.message_id != int(guild_config['message_id']):
        return # Không phải tin nhắn Reaction Role cần xử lý

    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    
    member = guild.get_member(payload.user_id)
    if not member: return

    # Ánh xạ Reaction Emoji sang Role Key
    emoji_name = payload.emoji.name
    role_key = REACTION_ROLES_CONFIG.get(emoji_name)

    if not role_key:
        return # Không phải emoji Hero/Monster

    new_role_id = ROLE_IDS.get(role_key)
    if not new_role_id: return

    new_role = guild.get_role(new_role_id)
    if not new_role: return

    # Lấy data người dùng từ Firestore
    user_data = await get_user_data(payload.user_id)
    if user_data is None: return

    # --- LOGIC CHỌN/ĐỔI ROLE ---
    
    # 1. Xác định Role Group cũ (nếu có)
    old_group_name = user_data.get('role_group')
    new_group_name = 'HERO' if role_key == 'HERO_GROUP' else 'MONSTER'
    
    # Nếu người dùng bấm lại vào Role Group đã chọn (hành vi hủy/bỏ qua)
    if old_group_name == new_group_name:
        # Giữ nguyên Role hiện tại. Discord sẽ tự động thêm Reaction, 
        # nhưng chúng ta không cần làm gì thêm ở đây nếu đã có Role.
        # Logic Hủy sẽ nằm trong on_raw_reaction_remove.
        
        # Nếu đã có Role Group này, không cần làm gì
        if member.roles.cache.has(new_role_id):
            return 
    
    # 2. Xử lý đổi nhóm (Remove Role cũ và Rank cũ)
    
    # Lấy ID Role Group cũ
    old_role_id = ROLE_IDS[f"{old_group_name.upper()}_GROUP"] if old_group_name else None
    
    # Nếu có Role Group cũ và nó khác Role Group mới
    if old_group_name and old_group_name != new_group_name:
        old_role = guild.get_role(old_role_id)
        if old_role and old_role in member.roles:
            await member.remove_roles(old_role, reason="Reaction Role: Đổi nhóm - Gỡ nhóm cũ")
            
        # Gỡ TẤT CẢ Role Rank cũ của nhóm đó (ví dụ: gỡ HERO_C, HERO_B...)
        group_prefix = 'HERO' if old_group_name == 'HERO' else 'M_' 
        all_rank_roles_ids = [id for key, id in ROLE_IDS.items()
                                 if key.startswith(group_prefix) and key not in ('HERO_GROUP', 'MONSTER_GROUP')]
        
        roles_to_remove = [r for r in member.roles if r.id in all_rank_roles_ids]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Reaction Role: Đổi nhóm - Gỡ Rank cũ")

    # 3. Gán Role Group mới
    if new_role not in member.roles:
        await member.add_roles(new_role, reason="Reaction Role: Chọn nhóm mới")

    # 4. Cập nhật data trong Firestore
    user_data['role_group'] = new_group_name
    
    # Reset level và xp về 0 nếu đổi nhóm (vì Rank phụ thuộc Level)
    if old_group_name and old_group_name != new_group_name:
        # user_data['level'] = 0 # Đã chú thích/xóa để KHÔNG reset
        # user_data['xp'] = 0    # Đã chú thích/xóa để KHÔNG reset
        pass # Giữ nguyên Level và XP khi đổi nhóm
        
    await save_user_data(payload.user_id, user_data)
    
    # Tự động cấp Rank (sẽ cấp Rank level 1 nếu level > 0)
    await update_user_level_and_roles(member, user_data)

    # (Tuỳ chọn) Gửi tin nhắn thông báo
    channel = bot.get_channel(payload.channel_id) or await bot.fetch_channel(payload.channel_id)
    if channel and member.roles.cache.has(new_role_id):
        try:
            await channel.send(f"✅ {member.mention} đã chọn nhóm **{new_group_name}**!", delete_after=5)
        except:
             pass # Có thể bot không có quyền gửi tin nhắn trong kênh đó


# Xử lý khi người dùng BỎ Reaction (Reaction Remove)
@bot.event
async def on_raw_reaction_remove(payload):
    # Bỏ qua nếu DB chưa sẵn sàng
    if db is None: return
    
    # Lấy thông tin Message ID của tin nhắn Reaction Role đã lưu
    config = await get_reaction_message_ids()
    guild_config = config.get(str(payload.guild_id))

    if not guild_config or payload.message_id != int(guild_config['message_id']):
        return # Không phải tin nhắn Reaction Role cần xử lý
    
    guild = bot.get_guild(payload.guild_id)
    if not guild: return

    # Lấy member (cần thiết vì payload.member không tồn tại trong remove)
    member = guild.get_member(payload.user_id)
    if not member or member.bot: return

    # Ánh xạ Reaction Emoji sang Role Key
    emoji_name = payload.emoji.name
    role_key = REACTION_ROLES_CONFIG.get(emoji_name)

    if not role_key: return

    role_id_to_remove = ROLE_IDS.get(role_key)
    if not role_id_to_remove: return

    role_to_remove = guild.get_role(role_id_to_remove)
    if not role_to_remove: return

    # --- LOGIC HỦY ROLE ---
    
    # Nếu người dùng bỏ Reaction, ta HỦY Role Group và gỡ Rank tương ứng
    if role_to_remove in member.roles:
        
        # 1. Gỡ Role Group
        await member.remove_roles(role_to_remove, reason="Reaction Role: Hủy chọn nhóm")
        
        # 2. Gỡ TẤT CẢ Role Rank cũ của nhóm đó
        group_name = 'HERO' if role_key == 'HERO_GROUP' else 'MONSTER'
        group_prefix = 'HERO' if group_name == 'HERO' else 'M_' 
        
        all_rank_roles_ids = [id for key, id in ROLE_IDS.items()
                                 if key.startswith(group_prefix) and key not in ('HERO_GROUP', 'MONSTER_GROUP')]
        
        roles_to_remove_rank = [r for r in member.roles if r.id in all_rank_roles_ids]
        if roles_to_remove_rank:
            await member.remove_roles(*roles_to_remove_rank, reason="Reaction Role: Hủy nhóm - Gỡ Rank")

        # 3. Cập nhật data trong Firestore: reset role_group, level, xp
        user_data = await get_user_data(payload.user_id)
        if user_data:
            user_data['role_group'] = None
            user_data['level'] = 0
            user_data['xp'] = 0
            await save_user_data(payload.user_id, user_data)


# ====== Lệnh /buff_xp (CHỈ DÀNH CHO GUILD OWNER) ======
@bot.tree.command(name="buff_xp", description="[OWNER ONLY] Thêm XP cho người dùng để kiểm tra hệ thống.")
@app_commands.describe(member="Người dùng muốn buff XP", amount="Số lượng XP muốn thêm")
@commands.is_owner() 
async def buff_xp(interaction: discord.Interaction, member: discord.Member, amount: int):
    # Kiểm tra Guild Owner (chủ server)
    if interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message(
            "❌ Lệnh này chỉ dành cho Chủ Server (Guild Owner).", ephemeral=True
        )
        return

    if amount <= 0:
        await interaction.response.send_message("❌ Số lượng XP phải lớn hơn 0.", ephemeral=True)
        return

    data = await get_user_data(member.id)

    if data is None:
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng. Vui lòng thử lại sau vài giây.", ephemeral=True)
        return
    
    if data['role_group'] is None:
        await interaction.response.send_message("❌ Người dùng chưa chọn Role Group (Hero/Monster). Vui lòng dùng lệnh `/select` hoặc Reaction Role.", ephemeral=True)
        return


    old_level = data['level']
    data['xp'] += amount

    # Cập nhật Level và Role
    await update_user_level_and_roles(member, data)

    # Lưu lại data sau khi buff
    await save_user_data(member.id, data)

    new_level = data['level']

    response_msg = f"✅ Đã thêm **{amount} XP** cho {member.mention}.\n"
    response_msg += f"XP hiện tại: **{data['xp']}** (Level **{new_level}**).\n"

    if new_level > old_level:
        response_msg += f"**🎉 Thăng cấp từ Level {old_level} lên Level {new_level}!**"

    await interaction.response.send_message(response_msg)


# ====== Lệnh /profile (Hiển thị thông tin người dùng) ======
@bot.tree.command(name="profile", description="Xem Level, XP và số tiền của bạn")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = await get_user_data(user_id)

    if data is None:
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng. Vui lòng thử lại sau vài giây.", ephemeral=True)
        return

    required_xp = get_required_xp(data['level'])

    # Xác định Rank hiện tại và tên
    rank_role_id = get_current_rank_role(data)
    rank_role = interaction.guild.get_role(rank_role_id) if rank_role_id else None
    rank_name = rank_role.name if rank_role else "Chưa xếp hạng"
    group_name = data.get('role_group', 'Chưa chọn nhóm')

    embed = discord.Embed(title=f"👤 Thông tin Hồ sơ của {interaction.user.display_name}", color=discord.Color.blue())
    embed.add_field(name="📜 Nhóm Role", value=group_name, inline=False)
    embed.add_field(name="⭐ Cấp Độ (Level)", value=f"**{data['level']}**", inline=True)
    embed.add_field(name="🏆 Rank/Hạng", value=rank_name, inline=True)
    embed.add_field(name="📈 XP", value=f"**{data['xp']}** / {required_xp} XP", inline=False)
    embed.add_field(name="💰 Fund", value=f"**{data['fund']}** {ROLE_IDS['FUND_EMOJI']}", inline=True)
    embed.add_field(name="🎟️ Coupon", value=f"**{data['coupon']}** {ROLE_IDS['COUPON_EMOJI']}", inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ====== Lệnh /daily (Điểm danh nhận tiền) ======
@bot.tree.command(name="daily", description="Điểm danh mỗi ngày để nhận Fund và Coupon (Reset 0:00)")
async def daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = await get_user_data(user_id)

    if data is None:
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng. Vui lòng thử lại sau vài giây.", ephemeral=True)
        return

    now = datetime.now()
    last_daily = data.get('last_daily')
    now_date = now.date()

    # Logic reset vào 0:00 (nửa đêm)
    if last_daily and last_daily.date() == now_date:
        # Đã điểm danh hôm nay, tính thời gian còn lại đến 0:00 ngày mai
        next_reset = datetime(now_date.year, now_date.month, now_date.day) + timedelta(days=1)
        remaining_time = next_reset - now
        
        hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        await interaction.response.send_message(
            f"⏳ Bạn đã điểm danh hôm nay rồi! Lượt điểm danh mới sẽ có lúc **0:00** (nửa đêm) hằng ngày. Vui lòng chờ **{hours} giờ {minutes} phút** nữa.",
            ephemeral=True
        )
        return

    # Tính thưởng
    fund_reward = random.randint(100, 300)
    coupon_reward = random.randint(50, 150)

    data['fund'] += fund_reward
    data['coupon'] += coupon_reward
    data['last_daily'] = now

    await save_user_data(user_id, data) # LƯU VÀO FIRESTORE

    await interaction.response.send_message(
        f"✅ Chúc mừng! Bạn đã điểm danh thành công và nhận được:\n"
        f"**+{fund_reward}** {ROLE_IDS['FUND_EMOJI']} Fund\n"
        f"**+{coupon_reward}** {ROLE_IDS['COUPON_EMOJI']} Coupon",
        ephemeral=True
    )

# ====== Lệnh /exchange (Quy đổi tiền tệ) ======
@bot.tree.command(name="exchange", description="Quy đổi 1 Fund = 1 Coupon")
@app_commands.describe(amount="Số Fund muốn quy đổi sang Coupon")
async def exchange(interaction: discord.Interaction, amount: int):
    user_id = interaction.user.id
    data = await get_user_data(user_id)

    if data is None:
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng. Vui lòng thử lại sau vài giây.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("❌ Số lượng phải lớn hơn 0.", ephemeral=True)
        return

    if data['fund'] < amount:
        await interaction.response.send_message(
            f"❌ Bạn không đủ Fund. Bạn chỉ có **{data['fund']}** {ROLE_IDS['FUND_EMOJI']}.",
            ephemeral=True
        )
        return

    data['fund'] -= amount
    data['coupon'] += amount

    await save_user_data(user_id, data) # LƯU VÀO FIRESTORE

    await interaction.response.send_message(
        f"✅ Quy đổi thành công!\n"
        f"Đã trừ **{amount}** {ROLE_IDS['FUND_EMOJI']} Fund.\n"
        f"Đã thêm **{amount}** {ROLE_IDS['COUPON_EMOJI']} Coupon.\n"
        f"Số dư Fund mới: **{data['fund']}**. Số dư Coupon mới: **{data['coupon']}**.",
        ephemeral=True
    )

# ====== Lệnh /select (Vẫn giữ lại cho người thích dùng lệnh) ======
@bot.tree.command(name="select", description="Chọn nhóm vai trò chính: Hero hoặc Monster")
async def select_group(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = await get_user_data(user_id)

    if data is None:
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng. Vui lòng thử lại sau vài giây.", ephemeral=True)
        return

    class RoleGroupSelect(discord.ui.View):
        def __init__(self, data):
            super().__init__(timeout=600)
            self.data = data
            self.current_group = data.get('role_group')

        async def _update_roles(self, i: discord.Interaction, new_group_name):
            member = i.user
            guild = i.guild

            new_group_key = f"{new_group_name.upper()}_GROUP"
            new_role_id = ROLE_IDS[new_group_key]
            new_role = guild.get_role(new_role_id)

            old_group_name = self.current_group
            old_role_id = ROLE_IDS[f"{old_group_name.upper()}_GROUP"] if old_group_name else None
            old_role = guild.get_role(old_role_id) if old_role_id else None

            msg = ""

            # Xử lý Hủy chọn (Toggle off)
            if old_group_name and old_group_name.lower() == new_group_name.lower():
                self.data['role_group'] = None
                if new_role:
                    await member.remove_roles(new_role, reason="Hủy chọn Role Group")
                msg = f"Đã **HỦY** chọn nhóm **{new_group_name.upper()}**."

                # Gỡ tất cả role rank cũ
                group_prefix = 'HERO' if old_group_name == 'HERO' else 'M_' 
                all_rank_roles_ids = [id for key, id in ROLE_IDS.items()
                                         if key.startswith(group_prefix) and key not in ('HERO_GROUP', 'MONSTER_GROUP')]
                
                roles_to_remove = [r for r in member.roles if r.id in all_rank_roles_ids]
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove, reason="Hủy Role Group: Gỡ Rank")

            # Xử lý Chọn mới/Đổi nhóm
            else:
                self.data['role_group'] = new_group_name.upper()

                if old_role and old_role in member.roles:
                    await member.remove_roles(old_role, reason="Chuyển Role Group: Gỡ nhóm cũ")
                    msg += f"Đã gỡ nhóm **{old_group_name.upper()}**.\n"

                if new_role and new_role not in member.roles:
                    await member.add_roles(new_role, reason="Chọn Role Group mới")

                msg += f"✅ Bạn đã chọn nhóm **{new_group_name.upper()}**."

                # Reset Level/XP nếu đổi nhóm
                if old_group_name and old_group_name != new_group_name:
                    # self.data['level'] = 0 # Đã chú thích/xóa để KHÔNG reset
                    # self.data['xp'] = 0    # Đã chú thích/xóa để KHÔNG reset
                    pass # Giữ nguyên Level và XP khi đổi nhóm
          
                # Tự động cấp Rank mới sau khi chọn nhóm
                await update_user_level_and_roles(member, self.data)

            self.current_group = self.data['role_group']
            await save_user_data(i.user.id, self.data) # LƯU VÀO FIRESTORE
            await i.response.edit_message(content=msg, view=self)

        @discord.ui.button(label="Hero", style=discord.ButtonStyle.primary, emoji="🦸‍♂️")
        async def hero_button(self, i: discord.Interaction, button: discord.ui.Button):
            await self._update_roles(i, "hero")

        @discord.ui.button(label="Monster", style=discord.ButtonStyle.danger, emoji="👹")
        async def monster_button(self, i: discord.Interaction, button: discord.ui.Button):
            await self._update_roles(i, "monster")

    await interaction.response.send_message(
        "Vui lòng chọn nhóm vai trò chính của bạn:",
        view=RoleGroupSelect(data),
        ephemeral=True
    )

# ====== Lệnh /all_in (Cược 80% số tiền) ======
# Định nghĩa các lựa chọn cho lệnh
CURRENCY_CHOICES = [
    app_commands.Choice(name="Fund", value="fund"),
    app_commands.Choice(name="Coupon", value="coupon"),
]

@bot.tree.command(name="all_in", description="Cược 80% Fund hoặc Coupon bạn đang có (Thắng x2, Thua mất hết)")
@app_commands.describe(currency="Loại tiền tệ bạn muốn cược")
@app_commands.choices(currency=CURRENCY_CHOICES)
async def all_in(interaction: discord.Interaction, currency: app_commands.Choice[str]):
    user_id = interaction.user.id
    data = await get_user_data(user_id)

    if data is None:
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng. Vui lòng thử lại sau vài giây.", ephemeral=True)
        return
    
    currency_key = currency.value # 'fund' hoặc 'coupon'
    currency_name = currency.name # 'Fund' hoặc 'Coupon'
    currency_emoji = ROLE_IDS[f"{currency_key.upper()}_EMOJI"]
    
    current_balance = data.get(currency_key, 0)

    # Tính số tiền cược (80% tổng số tiền, làm tròn xuống)
    bet_amount = int(current_balance * 0.8)

    if bet_amount <= 0:
        await interaction.response.send_message(
            f"❌ Bạn cần ít nhất 1 {currency_name} để cược 80% (cần > 1.25 {currency_name}).",
            ephemeral=True
        )
        return
    
    # --- LOGIC CƯỢC ---
    win = random.choice([True, False]) # 50% thắng, 50% thua
    
    old_balance = current_balance
    new_balance = 0
    gain_or_loss = 0
    
    if win:
        # Thắng: nhận lại số cược + tiền thắng (tổng cộng +bet_amount)
        data[currency_key] += bet_amount 
        gain_or_loss = bet_amount
        result_text = f"🎉 **THẮNG CUỘC!** Bạn đã nhân đôi số tiền cược **{bet_amount:,}** {currency_emoji} {currency_name}."
    else:
        # Thua: mất số tiền cược (-bet_amount)
        data[currency_key] -= bet_amount
        gain_or_loss = -bet_amount
        result_text = f"💀 **THUA CƯỢC!** Bạn đã mất số tiền cược **{bet_amount:,}** {currency_emoji} {currency_name}."

    new_balance = data[currency_key]

    await save_user_data(user_id, data) # LƯU VÀO FIRESTORE

    embed = discord.Embed(
        title=f"🎲 ALL IN - Cược {currency_name}", 
        description=result_text, 
        color=discord.Color.green() if win else discord.Color.red()
    )
    
    embed.add_field(name="Loại tiền cược", value=f"{currency_emoji} {currency_name}", inline=True)
    embed.add_field(name="Số tiền cược", value=f"**{bet_amount:,}**", inline=True)
    embed.add_field(name="Lãi/Lỗ", value=f"**{'+' if gain_or_loss >= 0 else ''}{gain_or_loss:,}**", inline=True)
    embed.add_field(name="Số dư cũ", value=f"{old_balance:,}", inline=True)
    embed.add_field(name="Số dư mới", value=f"**{new_balance:,}**", inline=True)
    
    await interaction.response.send_message(embed=embed)


# ====== Chạy bot ======
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("⚠️ Chưa có biến môi trường DISCORD_TOKEN!")
else:
    bot.run(TOKEN)
