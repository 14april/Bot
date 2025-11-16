import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
import asyncio

import config
import database
import localization # <-- THÊM NÀY
# Import các hàm helper từ cog level_system
from cogs.level_system import get_required_xp, get_current_rank_role

class UserCommandsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_lang(self, interaction: discord.Interaction):
        """Helper để lấy ngôn ngữ của user"""
        data = await database.get_user_data(interaction.user.id)
        if data is None:
            return 'vi' # Mặc định nếu có lỗi DB
        return data.get('language', 'vi')

    @app_commands.command(name="profile", description="Xem Level, XP và số tiền của bạn")
    async def profile(self, interaction: discord.Interaction):
        data = await database.get_user_data(interaction.user.id)
        user_lang = data.get('language', 'vi') # <-- LẤY NGÔN NGỮ

        if data is None:
            await interaction.response.send_message(localization.get_string(user_lang, 'db_error'), ephemeral=True) # <-- SỬA
            return

        required_xp = get_required_xp(data.get('level', 0))
        rank_role_id = get_current_rank_role(data)
        rank_role = interaction.guild.get_role(rank_role_id) if rank_role_id else None
        
        # <-- SỬA TITLE -->
        embed = discord.Embed(title=localization.get_string(user_lang, 'profile_title', name=interaction.user.display_name), color=discord.Color.blue())
        # <-- SỬA TÊN FIELD -->
        embed.add_field(name=localization.get_string(user_lang, 'profile_group'), value=data.get('role_group', localization.get_string(user_lang, 'profile_no_group')), inline=False)
        embed.add_field(name=localization.get_string(user_lang, 'profile_level'), value=f"**{data.get('level', 0)}**", inline=True)
        embed.add_field(name=localization.get_string(user_lang, 'profile_rank'), value=rank_role.name if rank_role else localization.get_string(user_lang, 'profile_no_rank'), inline=True)
        embed.add_field(name=localization.get_string(user_lang, 'profile_xp'), value=f"**{data.get('xp', 0):,}** / {required_xp:,}", inline=False)
        embed.add_field(name=localization.get_string(user_lang, 'profile_fund'), value=f"**{data.get('fund', 0):,}** {config.ROLE_IDS['FUND_EMOJI']}", inline=True)
        embed.add_field(name=localization.get_string(user_lang, 'profile_coupon'), value=f"**{data.get('coupon', 0):,}** {config.ROLE_IDS['COUPON_EMOJI']}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="daily", description="Điểm danh mỗi ngày để nhận thưởng (Reset 0:00)")
    async def daily(self, interaction: discord.Interaction):
        data = await database.get_user_data(interaction.user.id)
        user_lang = data.get('language', 'vi') # <-- LẤY NGÔN NGỮ

        if data is None:
            await interaction.response.send_message(localization.get_string(user_lang, 'db_error'), ephemeral=True) # <-- SỬA
            return

        last_daily = data.get('last_daily')
        if last_daily and last_daily.date() == datetime.now().date():
            await interaction.response.send_message(localization.get_string(user_lang, 'daily_already'), ephemeral=True) # <-- SỬA
            return

        fund_reward = random.randint(10_000_000_000, 999_000_000_000)
        coupon_reward = random.randint(10_000_000_000, 999_000_000_000)
        data['fund'] = data.get('fund', 0) + fund_reward
        data['coupon'] = data.get('coupon', 0) + coupon_reward
        data['last_daily'] = datetime.now()
        await database.save_user_data(interaction.user.id, data)
        
        # <-- SỬA -->
        await interaction.response.send_message(
            localization.get_string(
                user_lang, 
                'daily_success', 
                fund_reward=fund_reward, 
                fund_emoji=config.ROLE_IDS['FUND_EMOJI'], 
                coupon_reward=coupon_reward, 
                coupon_emoji=config.ROLE_IDS['COUPON_EMOJI']
            ),
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
        user_lang = data.get('language', 'vi') # <-- LẤY NGÔN NGỮ

        if data is None:
            return await interaction.followup.send(localization.get_string(user_lang, 'db_error'), ephemeral=True) # <-- SỬA
        if amount < 100:
            return await interaction.followup.send(localization.get_string(user_lang, 'exchange_min_amount'), ephemeral=True) # <-- SỬA

        source, target = ('fund', 'coupon') if exchange_type.value == "fund_to_coupon" else ('coupon', 'fund')
        if data.get(source, 0) < amount:
            return await interaction.followup.send(localization.get_string(user_lang, 'exchange_not_enough', source_name=source.capitalize()), ephemeral=True) # <-- SỬA
        
        data[source] -= amount
        data[target] = data.get(target, 0) + amount
        await database.save_user_data(interaction.user.id, data)
        # <-- SỬA -->
        await interaction.followup.send(localization.get_string(user_lang, 'exchange_success', amount=amount, source_name=source.capitalize(), target_name=target.capitalize()), ephemeral=True)


    @app_commands.command(name="all_in", description="Cược 80% Fund hoặc Coupon bạn đang có (Thắng x2-x5, Thua x1-x2)")
    @app_commands.describe(currency="Loại tiền tệ bạn muốn cược")
    @app_commands.choices(currency=config.CURRENCY_CHOICES) 
    async def all_in(self, interaction: discord.Interaction, currency: app_commands.Choice[str]):
        await interaction.response.defer() 
        
        user_id = interaction.user.id
        data = await database.get_user_data(user_id)
        user_lang = data.get('language', 'vi') # <-- LẤY NGÔN NGỮ

        if data is None:
            await interaction.followup.send(localization.get_string(user_lang, 'db_error'), ephemeral=True) # <-- SỬA
            return
        
        currency_key = currency.value 
        currency_name = currency.name 
        currency_emoji = config.ROLE_IDS[f"{currency_name.upper()}_EMOJI"]
        
        current_balance = data.get(currency_key, 0)
        bet_amount = int(current_balance * 0.8)

        if bet_amount <= 0:
            # <-- SỬA -->
            await interaction.followup.send(
                localization.get_string(user_lang, 'not_enough_currency', currency_name=currency_name),
                ephemeral=True
            )
            return
        
        slots = ["💎", "🍒", "🔔", "🍊", "🍋", "🍇", "🎁"]
        win = random.choice([True, False])
        
        # <-- SỬA -->
        embed = discord.Embed(
            title=localization.get_string(user_lang, 'all_in_title', currency_name=currency_name),
            description=localization.get_string(user_lang, 'all_in_description', mention=interaction.user.mention, bet_amount=bet_amount, currency_emoji=currency_emoji),
            color=discord.Color.gold()
        )
        s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
        embed.add_field(name=localization.get_string(user_lang, 'all_in_result'), value=f"**> {s1} | {s2} | {s3} <**") # <-- SỬA
        
        await interaction.followup.send(embed=embed)
        message = await interaction.original_response()

        for _ in range(3):
            await asyncio.sleep(0.75)
            s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
            embed.set_field_at(0, name=localization.get_string(user_lang, 'all_in_result'), value=f"**> {s1} | {s2} | {s3} <**") # <-- SỬA
            await message.edit(embed=embed)
        
        await asyncio.sleep(1)

        if win:
            win_emoji = currency_emoji
            final_slots = f"**> {win_emoji} | {win_emoji} | {win_emoji} <**"
        else:
            s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
            while s1 == s2 == s3:
                s1, s2, s3 = random.choice(slots), random.choice(slots), random.choice(slots)
            final_slots = f"**> {s1} | {s2} | {s3} <**"
        
        embed.set_field_at(0, name=localization.get_string(user_lang, 'all_in_result'), value=final_slots) # <-- SỬA
        await message.edit(embed=embed)
        await asyncio.sleep(1.5)

        old_balance = current_balance
        
        if win:
            multiplier = random.choices([2, 3, 5], weights=[60, 25, 15], k=1)[0]
            winnings = bet_amount * (multiplier - 1)
            data[currency_key] += winnings
            gain_or_loss = winnings
            result_text = localization.get_string(user_lang, 'all_in_win_lucky', multiplier=multiplier) # <-- SỬA
            embed.color = discord.Color.green()
        else:
            loss_multiplier = random.choices([1, 1.5, 2], weights=[70, 20, 10], k=1)[0]
            loss_amount = int(bet_amount * loss_multiplier)
            
            if loss_amount > current_balance:
                loss_amount = current_balance
                result_text = localization.get_string(user_lang, 'all_in_lose_all', loss_multiplier=loss_multiplier) # <-- SỬA
            else:
                if loss_multiplier == 1:
                    result_text = localization.get_string(user_lang, 'all_in_lose_normal') # <-- SỬA
                else:
                    result_text = localization.get_string(user_lang, 'all_in_lose_heavy', loss_multiplier=loss_multiplier) # <-- SỬA

            data[currency_key] -= loss_amount
            gain_or_loss = -loss_amount
            embed.color = discord.Color.red()

        await database.save_user_data(user_id, data)

        embed.description = result_text
        embed.clear_fields()
        # <-- SỬA TÊN FIELD -->
        embed.add_field(name=localization.get_string(user_lang, 'all_in_bet_currency'), value=f"{currency_emoji} {currency_name}", inline=True)
        embed.add_field(name=localization.get_string(user_lang, 'all_in_bet_amount'), value=f"**{bet_amount:,}**", inline=True)
        embed.add_field(name=localization.get_string(user_lang, 'all_in_profit_loss'), value=f"**{'+' if gain_or_loss >= 0 else ''}{gain_or_loss:,}**", inline=True)
        embed.add_field(name=localization.get_string(user_lang, 'all_in_old_balance'), value=f"{old_balance:,}", inline=True)
        embed.add_field(name=localization.get_string(user_lang, 'all_in_new_balance'), value=f"**{data[currency_key]:,}**", inline=True)
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
        
        user_lang = await self.get_lang(interaction) # <-- LẤY NGÔN NGỮ

        if interaction.user.id == recipient.id:
            return await interaction.followup.send(localization.get_string(user_lang, 'transfer_self'), ephemeral=True) # <-- SỬA
        if amount < 100:
            return await interaction.followup.send(localization.get_string(user_lang, 'min_amount_100'), ephemeral=True) # <-- SỬA

        sender_data = await database.get_user_data(interaction.user.id)
        currency_key = currency_type.value
        if sender_data.get(currency_key, 0) < amount:
            # <-- SỬA -->
            return await interaction.followup.send(localization.get_string(user_lang, 'not_enough_currency', currency_name=currency_key.capitalize()), ephemeral=True)

        recipient_data = await database.get_user_data(recipient.id)
        sender_data[currency_key] -= amount
        recipient_data[currency_key] = recipient_data.get(currency_key, 0) + amount
        await database.save_user_data(interaction.user.id, sender_data)
        await database.save_user_data(recipient.id, recipient_data)

        # <-- SỬA -->
        await interaction.followup.send(localization.get_string(user_lang, 'transfer_success', amount=amount, currency_key=currency_key.capitalize(), recipient_mention=recipient.mention), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UserCommandsCog(bot))
    print("✅ Cog 'user_commands' đã được tải.")
