import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio

# Import các file tiện ích
import database
import localization
import config # Mặc dù không dùng nhưng import để đồng bộ

class VoucherCalcCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_lang(self, interaction: discord.Interaction):
        """Helper để lấy ngôn ngữ của user"""
        data = await database.get_user_data(interaction.user.id)
        if data is None:
            return 'vi' # Mặc định nếu có lỗi DB
        return data.get('language', 'vi')

    # Hàm tính toán cốt lõi
    async def calculate_tickets(self, interaction: discord.Interaction, ticket_type_key: str, current_ticket: int, months: int, user_lang: str):
        now = datetime.now()
        current_month = now.month
        current_year = now.year

        per_month = 81 if ticket_type_key == "black" else 18
        results = []
        
        # Lấy tên vé đã được dịch
        if ticket_type_key == "black":
            ticket_type_loc = localization.get_string(user_lang, 'calc_ticket_type_black')
        else:
            ticket_type_loc = localization.get_string(user_lang, 'calc_ticket_type_relic')

        for i in range(1, months + 1):
            total = current_ticket + per_month * i
            
            target_month_raw = current_month + i
            target_year = current_year + (target_month_raw - 1) // 12
            target_month = (target_month_raw - 1) % 12 + 1
            
            month_str = f"**{target_month}/{target_year}**"
            
            # Sử dụng key localization cho dòng kết quả
            result_line = localization.get_string(user_lang, 'calc_ticket_result_line', ticket_type=ticket_type_loc)
            results.append(f"{month_str}: **{total} {result_line}**")

        # Gửi tin nhắn kết quả đã được dịch
        await interaction.followup.send(
            f"{localization.get_string(user_lang, 'calc_results_title', ticket_type=ticket_type_loc)}\n" + "\n".join(results),
            ephemeral=True
        )

    # Hàm fallback qua chat (nếu modal lỗi)
    async def fallback_chat(self, interaction: discord.Interaction, ticket_type_key: str, user_lang: str):
        
        if ticket_type_key == "black":
            ticket_type_loc = localization.get_string(user_lang, 'calc_ticket_type_black')
        else:
            ticket_type_loc = localization.get_string(user_lang, 'calc_ticket_type_relic')

        await interaction.followup.send(localization.get_string(user_lang, 'calc_fallback_prompt_ticket', ticket_type=ticket_type_loc), ephemeral=True)

        def check(msg):
            return msg.author == interaction.user and msg.channel == interaction.channel

        try:
            msg1 = await self.bot.wait_for("message", check=check, timeout=60)
            current_ticket = int(msg1.content)
        except (asyncio.TimeoutError, ValueError):
            await interaction.followup.send(localization.get_string(user_lang, 'calc_fallback_error'), ephemeral=True)
            return

        await interaction.followup.send(localization.get_string(user_lang, 'calc_fallback_prompt_month'), ephemeral=True)
        try:
            msg2 = await self.bot.wait_for("message", check=check, timeout=60)
            months = int(msg2.content)
            if not (1 <= months <= 12):
                raise ValueError
        except (asyncio.TimeoutError, ValueError):
            await interaction.followup.send(localization.get_string(user_lang, 'calc_fallback_error'), ephemeral=True)
            return

        await interaction.followup.send(localization.get_string(user_lang, 'calc_calculating'), ephemeral=True, delete_after=0.5)
        await self.calculate_tickets(interaction, ticket_type_key, current_ticket, months, user_lang)

        try:
            await msg1.delete()
            await msg2.delete()
        except discord.NotFound:
            pass # Tin nhắn đã bị xóa, không sao cả

    # Lệnh /calc chính
    @app_commands.command(name="calc", description="Tính số vé trong tương lai 📅")
    async def calc(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False, ephemeral=True)
        user_lang = await self.get_lang(interaction)
        
        # 'cog_self' để truyền instance của Cog vào Modal
        cog_self = self 

        # Định nghĩa Modal BÊN TRONG hàm lệnh để truy cập 'user_lang' và 'cog_self'
        class TicketModal(discord.ui.Modal):
            def __init__(self, ticket_type_key: str):
                self.ticket_type_key = ticket_type_key
                
                # Lấy tên vé đã dịch
                if ticket_type_key == "black":
                    self.ticket_type_loc = localization.get_string(user_lang, 'calc_ticket_type_black')
                else:
                    self.ticket_type_loc = localization.get_string(user_lang, 'calc_ticket_type_relic')

                super().__init__(title=localization.get_string(user_lang, 'calc_modal_title'))

                self.current_ticket_input = discord.ui.TextInput(
                    label=localization.get_string(user_lang, 'calc_modal_current', ticket_type=self.ticket_type_loc),
                    placeholder=localization.get_string(user_lang, 'calc_modal_current_placeholder'),
                    required=True,
                )
                self.months_input = discord.ui.TextInput(
                    label=localization.get_string(user_lang, 'calc_modal_months'),
                    placeholder=localization.get_string(user_lang, 'calc_modal_months_placeholder'),
                    required=True,
                )
                self.add_item(self.current_ticket_input)
                self.add_item(self.months_input)

            async def on_submit(self, i: discord.Interaction):
                try:
                    current_ticket = int(self.current_ticket_input.value)
                    months = int(self.months_input.value)
                    if not (1 <= months <= 12):
                        raise ValueError
                except ValueError:
                    await i.response.send_message(localization.get_string(user_lang, 'calc_invalid_input'), ephemeral=True)
                    return

                await i.response.defer(thinking=True, ephemeral=True)
                await cog_self.calculate_tickets(i, self.ticket_type_key, current_ticket, months, user_lang)

        # Định nghĩa View BÊN TRONG hàm lệnh
        class TicketSelect(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)

            @discord.ui.button(label=localization.get_string(user_lang, 'calc_button_black'), style=discord.ButtonStyle.primary, emoji="<:bt:1378705629182562304>")
            async def black_ticket(self, i: discord.Interaction, button: discord.ui.Button):
                try:
                    await i.response.send_modal(TicketModal("black"))
                except Exception:
                    # Nếu modal lỗi (ví dụ: bot khởi động lại), dùng fallback
                    await cog_self.fallback_chat(i, "black", user_lang)

            @discord.ui.button(label=localization.get_string(user_lang, 'calc_button_relic'), style=discord.ButtonStyle.success, emoji="<:ks:1378705636396892330>")
            async def relic_ticket(self, i: discord.Interaction, button: discord.ui.Button):
                try:
                    await i.response.send_modal(TicketModal("relic"))
                except Exception:
                    await cog_self.fallback_chat(i, "relic", user_lang)

        await interaction.followup.send(localization.get_string(user_lang, 'calc_prompt'), view=TicketSelect(), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoucherCalcCog(bot))
    print("✅ Cog 'voucher_calc' đã được tải.")
