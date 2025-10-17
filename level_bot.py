import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import random
import json

# --- FIREBASE IMPORTS ---
import firebase_admin
from firebase_admin import credentials, firestore
# ------------------------

# ==============================================================================
# CẤU HÌNH LƯU TRỮ DỮ LIỆU
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
    "HERO_C": 123456789012345680,
    "HERO_B": 123456789012345681,
    "HERO_A": 123456789012345682,
    "HERO_S": 123456789012345683,
    
    # Monster Ranks (Tiger, Demon, Dragon, God)
    "M_TIGER_LOW": 123456789012345684,
    "M_TIGER_MID": 123456789012345685,
    "M_TIGER_HIGH": 123456789012345686,
    "M_DEMON_LOW": 123456789012345687,
    "M_DEMON_MID": 123456789012345688,
    "M_DEMON_HIGH": 123456789012345689,
    "M_DRAGON_LOW": 123456789012345690,
    "M_DRAGON_MID": 123456789012345691,
    "M_DRAGON_HIGH": 123456789012345692,
    "M_GOD": 123456789012345693, 

    # Tiền tệ (Emoji/Icon)
    "FUND_EMOJI": "<:fund:123456789012345699>", 
    "COUPON_EMOJI": "<:coupon:123456789012345698>", 
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


# ====== Fake web server để Render không kill ======
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


# ====== Cấu hình intents ======
intents = discord.Intents.default()
intents.message_content = True 

# ====== Tạo bot ======
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
        
        # Khởi tạo ứng dụng Firebase
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Đã kết nối thành công với Firestore.")

    except Exception as e:
        print(f"❌ Lỗi khởi tạo Firebase/Firestore: {e}")
        db = None


async def get_user_data(user_id):
    """Lấy dữ liệu người dùng từ Firestore. Nếu chưa có, trả về dữ liệu mặc định."""
    if db is None:
        return None # Trả về None nếu DB chưa sẵn sàng
        
    doc_ref = db.collection(COLLECTION_NAME).document(str(user_id))
    try:
        doc = await doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            # Đảm bảo các trường datetime được khởi tạo (dù Firestore có thể xử lý)
            if 'last_xp_message' not in data:
                 data['last_xp_message'] = datetime.min
            if 'last_daily' not in data:
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
            # LƯU Ý: Không cần setDoc ở đây, chỉ khi có thay đổi mới lưu.
            return default_data

    except Exception as e:
        print(f"❌ Lỗi khi lấy dữ liệu cho user {user_id}: {e}")
        return None


async def save_user_data(user_id, data):
    """Lưu dữ liệu người dùng vào Firestore."""
    if db is None:
        return
        
    doc_ref = db.collection(COLLECTION_NAME).document(str(user_id))
    
    # Chuẩn hóa datetime.min để lưu trữ (Firestore không chấp nhận datetime.min)
    data_to_save = data.copy()
    if data_to_save['last_xp_message'] == datetime.min:
        data_to_save['last_xp_message'] = firestore.SERVER_TIMESTAMP
        
    try:
        await doc_ref.set(data_to_save)
        # print(f"💾 Đã lưu dữ liệu cho user {user_id} thành công.")
    except Exception as e:
        print(f"❌ Lỗi khi lưu dữ liệu cho user {user_id}: {e}")


# ==============================================================================
# CORE LOGIC FUNCTIONS
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
    """Kiểm tra và cập nhật Level, sau đó áp dụng Role Rank mới."""
    guild = member.guild
    level_changed = False
    
    # 1. Kiểm tra Level Up
    new_level = data['level']
    while data['xp'] >= get_required_xp(new_level):
        data['xp'] -= get_required_xp(new_level)
        new_level += 1
        level_changed = True
        try:
            await member.send(f"🎉 Chúc mừng {member.mention}! Bạn đã thăng cấp lên **Level {new_level}**!")
        except discord.Forbidden:
            pass

    if new_level != data['level']:
        data['level'] = new_level
        # Lưu lại vì Level đã thay đổi
        await save_user_data(member.id, data) 
    
    # 2. Xử lý Auto Role Rank 
    if data['role_group']:
        new_role_id = get_current_rank_role(data)
        
        if new_role_id:
            new_role = guild.get_role(new_role_id)
            if not new_role:
                return 

            group_prefix = 'HERO' if data['role_group'] == 'HERO' else 'M_' 
            all_rank_roles = [guild.get_role(id) for key, id in ROLE_IDS.items() 
                              if key.startswith(group_prefix) and key not in ('HERO_GROUP', 'MONSTER_GROUP')]
            
            roles_to_remove = [r for r in all_rank_roles if r and r in member.roles and r.id != new_role.id]
            
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Auto Role: Rank cũ")
            
            if new_role not in member.roles:
                await member.add_roles(new_role, reason="Auto Role: Rank mới")
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
        # Khởi tạo Firestore sau khi bot kết nối để đảm bảo môi trường đã sẵn sàng
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
        return
    
    if not isinstance(message.channel, discord.TextChannel):
        return

    user_id = message.author.id
    # Lấy data bất đồng bộ từ Firestore
    data = await get_user_data(user_id) 
    if data is None:
        return

    # Giới hạn XP: chỉ nhận XP sau 60 giây kể từ tin nhắn cuối cùng
    time_since_last_msg = datetime.now() - data.get('last_xp_message', datetime.min)
    
    if time_since_last_msg > timedelta(seconds=60):
        xp_gain = random.randint(5, 15)
        data['xp'] += xp_gain
        data['last_xp_message'] = datetime.now()
        
        # Cập nhật Level và Role (hàm này sẽ gọi save_user_data nếu level thay đổi)
        await update_user_level_and_roles(message.author, data)
        
        # Luôn lưu lại XP và last_xp_message
        await save_user_data(user_id, data) 
        
    await bot.process_commands(message) 


# ====== Lệnh /profile (Hiển thị thông tin người dùng) ======
@bot.tree.command(name="profile", description="Xem Level, XP và số tiền của bạn")
async def profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = await get_user_data(user_id)
    
    if data is None:
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng.", ephemeral=True)
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
@bot.tree.command(name="daily", description="Điểm danh mỗi ngày để nhận Fund và Coupon")
async def daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    data = await get_user_data(user_id)
    
    if data is None:
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng.", ephemeral=True)
        return
        
    now = datetime.now()
    cooldown_time = timedelta(hours=24)
    last_daily = data.get('last_daily')
    
    if last_daily and (now - last_daily < cooldown_time):
        remaining_time = last_daily + cooldown_time - now
        hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        await interaction.response.send_message(
            f"⏳ Bạn đã điểm danh hôm nay rồi! Vui lòng chờ **{hours} giờ {minutes} phút** nữa.",
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
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng.", ephemeral=True)
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
        await interaction.response.send_message("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng.", ephemeral=True)
        return
    
    class RoleGroupSelect(discord.ui.View):
        def __init__(self, data):
            super().__init__(timeout=600)
            self.data = data
            self.current_group = data.get('role_group')

        async def _update_roles(self, i: discord.Interaction, new_group_name):
            member = i.user
            guild = i.guild
            
            new_role_id = ROLE_IDS[f"{new_group_name.upper()}_GROUP"]
            new_role = guild.get_role(new_role_id)
            
            old_group_name = self.current_group
            old_role_id = ROLE_IDS[f"{old_group_name.upper()}_GROUP"] if old_group_name else None
            old_role = guild.get_role(old_role_id) if old_role_id else None
            
            msg = ""
            
            # Xử lý Hủy chọn (Toggle off)
            if old_group_name == new_group_name:
                self.data['role_group'] = None
                if new_role:
                    await member.remove_roles(new_role, reason="Hủy chọn Role Group")
                msg = f"Đã **HỦY** chọn nhóm **{new_group_name.upper()}**."
                
                # Gỡ tất cả role rank cũ
                group_prefix = 'HERO' if old_group_name == 'HERO' else 'M_' 
                all_rank_roles = [guild.get_role(id) for key, id in ROLE_IDS.items() 
                                  if key.startswith(group_prefix) and key not in ('HERO_GROUP', 'MONSTER_GROUP')]
                roles_to_remove = [r for r in all_rank_roles if r and r in member.roles]
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


# ====== Chạy bot ======
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("⚠️ Chưa có biến môi trường DISCORD_TOKEN!")
else:
    # LƯU Ý: Khởi tạo Firebase ở on_ready để đảm bảo tất cả async function sẵn sàng.
    bot.run(TOKEN)
