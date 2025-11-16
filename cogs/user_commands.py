import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
import asyncio

import config
import database
# Import các hàm helper từ cog level_system
from cogs.level_system import get_required_xp, get_current_rank_role

class UserCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Xem Level, XP và số tiền của bạn")
    async def profile(self, interaction: discord.Interaction):
        data = await database.get_user_data(interaction.user.id)
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
        embed.add_field(name="📈 XP", value=f"**{data.get('xp', 0):,}** / {required_xp:,}", inline=False)
        embed.add_field(name="💰 Fund", value=f"**{data.get('fund', 0):,}** {config.ROLE_IDS['FUND_EMOJI']}", inline=True)
        embed.add_field(name="🎟️ Coupon", value=f"**{data.get('coupon', 0):,}** {config.ROLE_IDS['COUPON_EMOJI']}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="daily", description="Điểm danh mỗi ngày để nhận thưởng (Reset 0:00)")
    async def daily(self, interaction: discord.Interaction):
        data = await database.get_user_data(interaction.user.id)
        if data is None:
            await interaction.response.send_message("❌ Lỗi cơ sở dữ liệu.", ephemeral=True)
            return

        last_daily = data.get('last_daily')
        if last_daily and last_daily.date() == datetime.now().date():
            await interaction.response.send_message("⏳ Bạn đã điểm danh hôm nay rồi!", ephemeral=True)
            return

        fund_reward = random.randint(10_000_000_000, 999_000_000_000)
        coupon_reward = random.randint(10_000_000_000, 999_000_000_000)
        data['fund'] = data.get('fund', 0) + fund_reward
        data['coupon'] = data.get('coupon', 0) + coupon_reward
        data['last_daily'] = datetime.now()
        await database.save_user_data(interaction.user.id, data)
        await interaction.response.send_message(
            f"✅ Điểm danh thành công! Nhận được:\n"
            f"**+{fund_reward:,}** {config.ROLE_IDS['FUND_EMOJI']} & **+{coupon_reward:,}** {config.ROLE_IDS['COUPON_EMOJI']}",
            ephemeral=True
        )

    @app_commands.command(name="exchange", description="Trao đổi tiền tệ Fund 🔄 Coupon (Tỷ giá 1:1).")
    @app_commands.describe(exchange_type="Loại tiền bạn muốn ĐỔI.", amount="Số lượng (tối thiểu 100).")
    @app_commands.choices(exchange_type=[
        app_commands.Choice(name="💰 Fund -> Coupon", value="fund_to_coupon"),
        app_commands.Choice(name="🎟️ Coupon -> Fund", value="coupon_to_fund"),
    ])
    async def exchange(self, interaction: discord.Interaction, exchange_type: app_commands.Choice[str], amount: int):
        await interaction.response.defer(ephemeral=True)
        data = await database.get_user_data(interaction.user.id)
        if data is None:
            return await interaction.followup.send("❌ Lỗi cơ sở dữ liệu.", ephemeral=True)
        if amount < 100:
            return await interaction.followup.send("❌ Số tiền trao đổi tối thiểu là 100.", ephemeral=True)

        source, target = ('fund', 'coupon') if exchange_type.value == "fund_to_coupon" else ('coupon', 'fund')
        if data.get(source, 0) < amount:
            return await interaction.followup.send(f"❌ Bạn không đủ {source.capitalize()}.", ephemeral=True)
        
        data[source] -= amount
        data[target] = data.get(target, 0) + amount
        await database.save_user_data(interaction.user.id, data)
        await interaction.followup.send(f"✅ Đã đổi **{amount:,}** {source.capitalize()} sang {target.capitalize()}.", ephemeral=True)


    @app_commands.command(name="all_in", description="Cược 80% Fund hoặc Coupon bạn đang có (Thắng x2-x5, Thua x1-x2)")
    @app_commands.describe(currency="Loại tiền tệ bạn muốn cược")
    @app_commands.choices(currency=config.CURRENCY_CHOICES) # Dùng biến từ config
    async def all_in(self, interaction: discord.Interaction, currency: app_commands.Choice[str]):
        await interaction.response.defer() 
        user_id = interaction.user.id
        data = await database.get_user_data(user_id)
        if data is None:
            await interaction.followup.send("❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng.", ephemeral=True)
            return
        
        currency_key = currency.value 
        currency_name = currency.name 
        currency_emoji = config.ROLE_IDS[f"{currency_name.upper()}_EMOJI"]
        
        current_balance = data.get(currency_key, 0)
        bet_amount = int(current_balance * 0.8)

        if bet_amount <= 0:
            await interaction.followup.send(
                f"❌ Bạn không có đủ {currency_name} để cược.",
                ephemeral=True
            )
            return
        
        # (Copy toàn bộ logic cược /all_in từ file cũ vào đây)
        slots = ["💎", "🍒", "🔔", "🍊", "🍋", "🍇", "🎁"]
        win = random.choice([True, False])
        
        embed = discord.Embed(
            title=f"🎲 ALL IN - Cược {currency_name}",
            description=f"{interaction.user.mention} cược **{bet_amount:,}** {currency_emoji}...",
            color=discord.Color.gold()
        )
        s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
        embed.add_field(name="Kết quả", value=f"**> {s1} | {s2} | {s3} <**")
        
        await interaction.followup.send(embed=embed)
        message = await interaction.original_response()

        for _ in range(3):
            await asyncio.sleep(0.75)
            s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
            embed.set_field_at(0, name="Kết quả", value=f"**> {s1} | {s2} | {s3} <**")
            await message.edit(embed=embed)
        
        await asyncio.sleep(1)
        # ... (Toàn bộ logic xử lý thắng/thua) ...
        if win:
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
            multiplier = random.choices([2, 3, 5], weights=[60, 25, 15], k=1)[0]
            winnings = bet_amount * (multiplier - 1)
            data[currency_key] += winnings
            gain_or_loss = winnings
            result_text = f"🎉 **THẮNG LỚN!** Bạn đã trúng **x{multiplier}** số tiền cược!"
            embed.color = discord.Color.green()
        else:
            loss_multiplier = random.choices([1, 1.5, 2], weights=[70, 20, 10], k=1)[0]
            loss_amount = int(bet_amount * loss_multiplier)
            if loss_amount > current_balance:
                loss_amount = current_balance
                result_text = f"💀 **THUA CƯỢC!** Bạn đã mất **TẤT CẢ** (trúng x{loss_multiplier:.1f} nhưng bị giới hạn)!"
            else:
                if loss_multiplier == 1:
                    result_text = f"💀 **THUA CƯỢC!** Bạn mất số tiền cược."
                else:
                    result_text = f"💀 **THUA ĐẬM!** Bạn bị phạt x{loss_multiplier:.1f} số tiền cược!"
            data[currency_key] -= loss_amount
            gain_or_loss = -loss_amount
            embed.color = discord.Color.red()

        await database.save_user_data(user_id, data)
        # ... (phần còn lại của code embed) ...
        embed.description = result_text
        embed.clear_fields()
        embed.add_field(name="Loại tiền cược", value=f"{currency_emoji} {currency_name}", inline=True)
        embed.add_field(name="Số tiền cược", value=f"**{bet_amount:,}**", inline=True)
        embed.add_field(name="Lãi/Lỗ", value=f"**{'+' if gain_or_loss >= 0 else ''}{gain_or_loss:,}**", inline=True)
        embed.add_field(name="Số dư cũ", value=f"{old_balance:,}", inline=True)
        embed.add_field(name="Số dư mới", value=f"**{data[currency_key]:,}**", inline=True)
        await message.edit(embed=embed)


    @app_commands.command(name="transfer", description="Chuyển Fund/Coupon cho người chơi khác.")
    @app_commands.describe(
        recipient="Người muốn chuyển tiền cho.",
        currency_type="Loại tiền muốn chuyển.",
        amount="Số lượng (tối thiểu 100)."
    )
    @app_commands.choices(currency_type=[
        app_commands.Choice(name="💰 Fund", value="fund"),
        app_commands.Choice(name="🎟️ Coupon", value="coupon"),
    ])
    async def transfer_command(self, interaction: discord.Interaction, recipient: discord.Member, currency_type: app_commands.Choice[str], amount: int):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id == recipient.id:
            return await interaction.followup.send("❌ Bạn không thể tự chuyển cho mình.", ephemeral=True)
        if amount < 100:
            return await interaction.followup.send("❌ Số tiền chuyển tối thiểu là 100.", ephemeral=True)

        sender_data = await database.get_user_data(interaction.user.id)
        currency_key = currency_type.value
        if sender_data.get(currency_key, 0) < amount:
            return await interaction.followup.send(f"❌ Bạn không đủ {currency_key.capitalize()}.", ephemeral=True)

        recipient_data = await database.get_user_data(recipient.id)
        sender_data[currency_key] -= amount
        recipient_data[currency_key] = recipient_data.get(currency_key, 0) + amount
        await database.save_user_data(interaction.user.id, sender_data)
        await database.save_user_data(recipient.id, recipient_data)

        await interaction.followup.send(f"✅ Đã chuyển **{amount:,}** {currency_key.capitalize()} cho {recipient.mention}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommandsCog(bot))
    print("✅ Cog 'user_commands' đã được tải.")
