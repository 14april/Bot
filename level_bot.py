import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Import các file tiện ích mới
import keep_alive
import database
import config

# Tải biến môi trường (an toàn khi dùng trên Railway)
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ LỖI: Không tìm thấy DISCORD_TOKEN trong biến môi trường.")
    exit()

# Cấu hình intents (giữ nguyên từ file cũ)
intents = discord.Intents.default()
intents.members = True 
intents.reactions = True
intents.message_content = True

# Khởi tạo bot (giữ nguyên từ file cũ)
bot = commands.Bot(command_prefix="!", intents=intents)

# Danh sách các Cogs (tên file) cần tải
INITIAL_EXTENSIONS = [
    'cogs.level_system',
    'cogs.user_commands',
    'cogs.leaderboard',
    'cogs.reaction_roles',
    'cogs.admin_commands',
    'cogs.language_command',
]

@bot.event
async def on_ready():
    # Giữ nguyên logic kết nối DB từ file cũ
    retry_count = 0
    max_retries = 10 
    while database.db is None and retry_count < max_retries:
        print(f"🔄 Thử kết nối Firestore lần {retry_count + 1}...")
        database.initialize_firestore() 
        if database.db is None:
            retry_count += 1
            await asyncio.sleep(2 * retry_count) 
        else:
            break 
    if database.db is None:
        print("🛑 Lỗi nghiêm trọng: KHÔNG THỂ kết nối Firestore sau nhiều lần thử.")
        return # Ngăn bot chạy nếu không có DB
    
    print(f"✅ Bot Level/Tiền tệ đã đăng nhập thành công: {bot.user}")

    # Giữ nguyên logic sync command từ file cũ
    if not config.GUILD_ID:
        print("⚠️ Vui lòng thay thế GUILD_ID trong config.py.")
    else:
        guild = discord.Object(id=config.GUILD_ID)
        try:
            bot.tree.copy_global_to(guild=guild)
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync() 
            synced = await bot.tree.sync(guild=guild)
            print(f"🔁 Đã đồng bộ {len(synced)} lệnh slash CHỈ cho server ID: {config.GUILD_ID}.")
        except Exception as e:
            print(f"❌ Lỗi sync command cho server {config.GUILD_ID}: {e}")

# Hàm chính để chạy bot
async def main():
    # Chạy server ping
    keep_alive.start_keep_alive()
    
    # Tải tất cả Cogs
    print("--- Đang tải Cogs ---")
    for extension in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(extension)
        except Exception as e:
            print(f"❌ Lỗi khi tải Cog {extension}: {e}")
    print("---------------------")

    # Chạy bot với token
    async with bot:
        await bot.start(TOKEN)

# Khởi chạy bot
if __name__ == "__main__":
    # Ghi chú: Xóa hàm on_message ở đây vì nó đã được chuyển vào Cog
    # Bot sẽ tự động xử lý process_commands
    asyncio.run(main())
