# File này chứa tất cả các chuỗi văn bản cho bot
LANG_STRINGS = {
    'vi': {
        # === LỖI CHUNG ===
        'db_error': "❌ Lỗi cơ sở dữ liệu. Vui lòng thử lại sau.",
        'min_amount_100': "❌ Số tiền tối thiểu là 100.",
        'not_enough_fund': "❌ Bạn không đủ Fund.",
        'not_enough_coupon': "❌ Bạn không đủ Coupon.",
        'not_enough_currency': "❌ Bạn không có đủ {currency_name} để cược.",
        'generic_error': "❌ Đã xảy ra lỗi: {error}",

        # === LỆNH ADMIN ===
        'admin_buff_gt_zero': "❌ Số tiền phải lớn hơn 0.",
        'admin_buff_success': "✅ Đã thêm **{amount:,}** {currency_key} cho {member_mention}.",
        'admin_not_owner': "⛔ Lệnh này chỉ dành cho Owner của Bot.",
        'setup_config_error': "❌ Lỗi cấu hình: Vui lòng thay ID mẫu trong ROLE_IDS.",
        'setup_setting_up': "Đang thiết lập...",
        'setup_success': "✅ Đã thiết lập thành công! Vui lòng ghim tin nhắn này.",
        'setup_error': "❌ Lỗi: Bot không thể gửi tin nhắn hoặc thêm reaction.",

        # === LỆNH NGÔN NGỮ ===
        'lang_changed_success': "✅ Ngôn ngữ của bạn đã được đổi thành Tiếng Việt.",

        # === LỆNH LEADERBOARD ===
        'lb_db_not_ready': "❌ Lỗi: Cơ sở dữ liệu chưa sẵn sàng.",
        'lb_query_error': "❌ Đã xảy ra lỗi khi truy vấn bảng xếp hạng.",
        'lb_hero_title': "🏆 Bảng Xếp Hạng Hero - {rank_name}",
        'lb_hero_desc': "Top 10 người chơi có Level và XP cao nhất trong rank {rank_name}.",
        'lb_monster_title': "🏆 Bảng Xếp Hạng Monster - {rank_name}",
        'lb_monster_desc': "Top 10 quái vật có Level và XP cao nhất trong rank {rank_name}.",
        'lb_no_players': "Không tìm thấy người chơi nào ở rank này.",
        'lb_user_id': "Người dùng ID: {id}",

        # === HỆ THỐNG LEVEL (DM) ===
        'level_up_dm': (
            "🎉 Chúc mừng {mention}! Bạn đã thăng cấp lên **Level {new_level}**!\n"
            "🎁 Thưởng Level Up: **+{reward_fund:,}** {fund_emoji} Fund và **+{reward_coupon:,}** {coupon_emoji} Coupon!"
        ),
        'rank_up_dm': "🌟 Bạn đã được thăng cấp Rank thành **{new_role_name}**!",

        # === LỆNH NGƯỜI DÙNG ===
        'profile_title': "👤 Hồ sơ của {name}",
        # ... (các key khác của bạn)
        'transfer_self': "❌ Bạn không thể tự chuyển cho mình.",
        'transfer_success': "✅ Đã chuyển **{amount:,}** {currency_key} cho {recipient_mention}.",
        
        # === VOUCHER CALC (MỚI) ===
        'calc_prompt': "🎫 Chọn loại vé bạn muốn tính:",
        'calc_button_black': "Vé đen",
        'calc_button_relic': "Vé kỉ vật",
        'calc_modal_title': "Tính vé trong tương lai",
        'calc_modal_current': "Số vé {ticket_type} hiện tại",
        'calc_modal_current_placeholder': "Nhập số vé (vd: 100)",
        'calc_modal_months': "Số tháng muốn tính (1–12)",
        'calc_modal_months_placeholder': "Nhập số tháng (vd: 3)",
        'calc_invalid_input': "⚠️ Dữ liệu không hợp lệ. Vui lòng kiểm tra lại số vé và số tháng (1-12).",
        'calc_fallback_prompt_ticket': "Nhập **Số vé {ticket_type} hiện tại**:",
        'calc_fallback_prompt_month': "Nhập **Số tháng cần tính (1–12)**:",
        'calc_fallback_error': "⚠️ Dữ liệu không hợp lệ hoặc hết thời gian nhập.",
        'calc_calculating': "Đang tính toán...",
        'calc_results_title': "📊 Kết quả dự tính cho **{ticket_type}** (Tính từ tháng sau):",
        'calc_ticket_type_black': "đen",
        'calc_ticket_type_relic': "kỉ vật",
        'calc_ticket_result_line': "vé {ticket_type}",
    },
    'en': {
        # === LỖI CHUNG ===
        'db_error': "❌ Database error. Please try again later.",
        # ... (các key khác của bạn)
        'generic_error': "❌ An error occurred: {error}",

        # === LỆNH ADMIN ===
        'admin_not_owner': "⛔ This command is for the Bot Owner only.",
        # ... (các key khác của bạn)
        'setup_error': "❌ Error: The bot could not send a message or add reactions.",

        # === LỆNH NGÔN NGỮ ===
        'lang_changed_success': "✅ Your language has been changed to English.",

        # === LỆNH LEADERBOARD ===
        'lb_db_not_ready': "❌ Error: Database is not ready.",
         # ... (các key khác của bạn)
        'lb_user_id': "User ID: {id}",

        # === HỆ THỐNG LEVEL (DM) ===
        'level_up_dm': (
            "🎉 Congratulations {mention}! You have leveled up to **Level {new_level}**!\n"
            "🎁 Level Up Reward: **+{reward_fund:,}** {fund_emoji} Fund and **+{reward_coupon:,}** {coupon_emoji} Coupon!"
        ),
        'rank_up_dm': "🌟 You have been promoted to **{new_role_name}** rank!",

        # === LỆNH NGƯỜI DÙNG ===
        'profile_title': "👤 {name}'s Profile",
        # ... (các key khác của bạn)
        'transfer_self': "❌ You cannot transfer to yourself.",
        'transfer_success': "✅ Transferred **{amount:,}** {currency_key} to {recipient_mention}.",

        # === VOUCHER CALC (MỚI) ===
        'calc_prompt': "🎫 Select the ticket type you want to calculate:",
        'calc_button_black': "Black Ticket",
        'calc_button_relic': "Relic Ticket",
        'calc_modal_title': "Calculate future tickets",
        'calc_modal_current': "Current {ticket_type} tickets",
        'calc_modal_current_placeholder': "Enter ticket count (e.g., 100)",
        'calc_modal_months': "Number of months to calculate (1–12)",
        'calc_modal_months_placeholder': "Enter number of months (e.g., 3)",
        'calc_invalid_input': "⚠️ Invalid data. Please check the ticket count and months (1-12).",
        'calc_fallback_prompt_ticket': "Enter **Current {ticket_type} tickets**:",
        'calc_fallback_prompt_month': "Enter **Number of months to calculate (1–12)**:",
        'calc_fallback_error': "⚠️ Invalid data or input timed out.",
        'calc_calculating': "Calculating...",
        'calc_results_title': "📊 Estimated results for **{ticket_type}** (Starting next month):",
        'calc_ticket_type_black': "black",
        'calc_ticket_type_relic': "relic",
        'calc_ticket_result_line': "{ticket_type} tickets",
    }
}

def get_string(lang: str, key: str, **kwargs):
    """
    Lấy chuỗi văn bản theo ngôn ngữ và key.
    kwargs dùng để format chuỗi (ví dụ: {name}, {amount})
    """
    if lang not in LANG_STRINGS:
        lang = 'vi' # Mặc định là Tiếng Việt
    
    string_template = LANG_STRINGS[lang].get(key)
    
    if string_template is None:
        # Nếu không tìm thấy, thử lấy bằng tiếng Anh
        string_template = LANG_STRINGS['en'].get(key)
        if string_template is None:
            # Nếu vẫn không tìm thấy, trả về thông báo lỗi
            return f"⚠️ Missing string for key: '{key}' in all languages"

    if kwargs:
        try:
            return string_template.format(**kwargs)
        except KeyError as e:
            return f"⚠️ String format error for key '{key}': Missing {e}"
    
    return string_template
