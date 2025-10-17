import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
import random
import json
import math # Import math để dùng math.floor (hoặc dùng int() cho đơn giản)

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

# Dữ liệu sẽ được cache tạm thời, nhưng nguồn chính là Firestore
db = None

# Cấu hình Role ID (BẠN CẦN THAY THẾ CHÚNG BẰNG ID THỰC CỦA SERVER BẠN)
ROLE_IDS = {
    # Nhóm vai trò chính
    "HERO_GROUP": 123456789012345678,
    "MONSTER_GROUP": 123456789012345679,

    # Hero Ranks (C, B, A, S)
    "HERO_C": 1428609299550175293,
    "HERO_B": 1428609397906477116,
    "HERO_A": 1428609426117492756,
    "HERO_S": 1428609449173454859,

    # Monster Ranks (Tiger, Demon, Dragon, God)
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

    # Tiền tệ (Emoji/Icon)
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

# --- CẬP NHẬT THEO YÊU CẦU ---
# Giảm cooldown nhận XP khi nhắn tin từ 60s xuống 5s
XP_COOLDOWN_SECONDS = 5
# -----------------------------


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
        # Lấy nội dung JSON của Service Account từ biến môi trường
        cred_json = os.getenv("FIREBASE_CREDENTIALS")
        if not cred_json:
            print("❌ Lỗi: Không tìm thấy biến môi trường FIREBASE_CREDENTIALS.")
            return

        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)

        # Khởi tạo ứng dụng Firebase. Nếu đã khởi tạo rồi thì không gọi lại.
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            
        db = firestore.client()
        print("✅ Đã kết nối thành công với Firestore.")

    except Exception as e:
        print(f"❌ Lỗi khởi tạo Firebase/Firestore: {e}. Vui lòng kiểm tra FIREBASE_CREDENTIALS.")
        db = None # Đảm bảo db là None nếu thất bại


async def get_user_data(user_id):
    """Lấy dữ liệu người dùng từ Firestore. Nếu chưa có, trả về dữ liệu mặc định."""
    global db
    if db is None:
        # Thử khởi tạo lại DB trong trường hợp on_ready chưa chạy hoặc thất bại
        initialize_firestore() 
        if db is None:
            # Nếu vẫn không kết nối được sau khi thử lại, trả về None
            return None 

    doc_ref = db.collection(COLLECTION_NAME).document(str(user_id))
    try:
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()

            # Xử lý các trường datetime từ Firestore Timestamp
            if data.get('last_xp_message') and isinstance(data['last_xp_message'], firestore.client.datetime.datetime):
                data['last_xp_message'] = data['last_xp_message'].replace(tzinfo=None)
            else:
                 data['last_xp_message'] = datetime.min

            if data.get('last_daily') and isinstance(data['last_daily'], firestore.client.datetime.datetime):
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
        # Rất có thể là lỗi kết nối/mạng, đặt db về None để kích hoạt khởi tạo lại
        db = None 
        return None


async def save_user_data(user_id, data):
    """Lưu dữ liệu người dùng vào Firestore."""
    global db
    if db is None:
        # Thử khởi tạo lại DB trong trường hợp on_ready chưa chạy hoặc thất bại
        initialize_firestore() 
        if db is None:
            print(f"🛑 Không thể lưu dữ liệu cho user {user_id}. DB chưa sẵn sàng.")
            return

    doc_ref = db.collection(COLLECTION_NAME).document(str(user_id))

    # Chuẩn bị dữ liệu để lưu
    data_to_save = data.copy()

    # Firestore có thể xử lý datetime objects, nhưng phải loại bỏ datetime.min
    if data_to_save['last_xp_message'] == datetime.min:
        # Sử dụng Server Timestamp nếu giá trị là datetime.min
        data_to_save['last_xp_message'] = firestore.SERVER_TIMESTAMP

    try:
        doc_ref.set(data_to_save)
    except Exception as e:
        print(f"❌ Lỗi khi lưu dữ liệu cho user {user_id}: {e}")
        # Rất có thể là lỗi kết nối/mạng, đặt db về None để kích hoạt khởi tạo lại
        db = None


# ==============================================================================
# CORE LOGIC FUNCTIONS: XP, LEVEL, ROLE
# ==============================================================================

def get_required_xp(level):
    """Tính XP cần thiết để lên level tiếp theo."""
    # Công thức: BASE * (Level + 1) ^ SCALING
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
    max_level_hero = max(LEVEL_TIERS['HERO'].keys())
    max_level_monster = max(LEVEL_TIERS['MONSTER'].keys())
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
        # Thưởng Fund ngẫu nhiên (50-150) và Coupon ngẫu nhiên (10-30)
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

    # 2. Xử lý Auto Role Rank
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
    if db is None:
        initialize_firestore()
        if db is None:
            print("🛑 Lỗi nghiêm trọng: Không thể kết nối Firestore. Dữ liệu sẽ không được lưu trữ.")

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
        # Nếu db là None, thử khởi tạo lại ngay tại đây
        if db is None:
            initialize_firestore()
            if db is None:
                # Nếu vẫn không được, bỏ qua xử lý tin nhắn
                await bot.process_commands(message) 
                return

    if not isinstance(message.channel, discord.TextChannel):
        await bot.process_commands(message)
        return

    user_id = message.author.id
    # Lấy data bất đồng bộ từ Firestore
    data = await get_user_data(user_id)
    if data is None:
        # Nếu data là None, có nghĩa là DB chưa sẵn sàng (đã thử khởi tạo lại)
        await bot.process_commands(message)
        return

    # Giới hạn XP: chỉ nhận XP sau XP_COOLDOWN_SECONDS giây kể từ tin nhắn cuối cùng
    MIN_XP_COOLDOWN = timedelta(seconds=XP_COOLDOWN_SECONDS)
    last_xp = data.get('last_xp_message', datetime.min)

    # Đảm bảo last_xp là datetime object
    if not isinstance(last_xp, datetime):
        last_xp = datetime.min

    time_since_last_msg = datetime.now() - last_xp

    if time_since_last_msg > MIN_XP_COOLDOWN:
        xp_gain = random.randint(5, 15)
        data['xp'] += xp_gain
        data['last_xp_message'] = datetime.now()

        # Cập nhật Level và Role (hàm này sẽ gọi save_user_data nếu level thay đổi)
        await update_user_level_and_roles(message.author, data)

        # Luôn lưu lại XP và last_xp_message (trừ khi đã được lưu trong update_user_level_and_roles)
        # Tải lại data để so sánh level cũ, tránh trường hợp bị mất data nếu update_user_level_and_roles đã save
        current_db_data = await get_user_data(user_id)
        if current_db_data and data['level'] == current_db_data.get('level', 0):
            await save_user_data(user_id, data)

    await bot.process_commands(message)


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
    rank_name = interaction.guild.get_role(rank_role_id).name if rank_role_id else "Chưa xếp hạng"
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

# ====== Lệnh /select (Chọn Role Group Hero/Monster) ======
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
