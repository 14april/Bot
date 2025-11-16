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
        # /profile
        'profile_title': "👤 Hồ sơ của {name}",
        'profile_group': "📜 Nhóm",
        'profile_no_group': "Chưa chọn",
        'profile_level': "⭐ Level",
        'profile_rank': "🏆 Rank",
        'profile_no_rank': "Chưa có",
        'profile_xp': "📈 XP",
        'profile_fund': "💰 Fund",
        'profile_coupon': "🎟️ Coupon",
        
        # /daily
        'daily_already': "⏳ Bạn đã điểm danh hôm nay rồi!",
        'daily_success': "✅ Điểm danh thành công! Nhận được:\n**+{fund_reward:,}** {fund_emoji} & **+{coupon_reward:,}** {coupon_emoji}",

        # /exchange
        'exchange_min_amount': "❌ Số tiền trao đổi tối thiểu là 100.",
        'exchange_not_enough': "❌ Bạn không đủ {source_name}.",
        'exchange_success': "✅ Đã đổi **{amount:,}** {source_name} sang {target_name}.",

        # /all_in
        'all_in_title': "🎲 ALL IN - Cược {currency_name}",
        'all_in_description': "{mention} cược **{bet_amount:,}** {currency_emoji}...",
        'all_in_result': "Kết quả",
        'all_in_win_lucky': "🎉 **THẮNG LỚN!** Bạn đã trúng **x{multiplier}** số tiền cược!",
        'all_in_lose_normal': "💀 **THUA CƯỢC!** Bạn mất số tiền cược.",
        'all_in_lose_heavy': "💀 **THUA ĐẬM!** Bạn bị phạt x{loss_multiplier:.1f} số tiền cược!",
        'all_in_lose_all': "💀 **THUA CƯỢC!** Bạn đã mất **TẤT CẢ** (trúng x{loss_multiplier:.1f} nhưng bị giới hạn)!",
        'all_in_bet_currency': "Loại tiền cược",
        'all_in_bet_amount': "Số tiền cược",
        'all_in_profit_loss': "Lãi/Lỗ",
        'all_in_old_balance': "Số dư cũ",
        'all_in_new_balance': "Số dư mới",
        
        # /transfer
        'transfer_self': "❌ Bạn không thể tự chuyển cho mình.",
        'transfer_success': "✅ Đã chuyển **{amount:,}** {currency_key} cho {recipient_mention}.",

    },
    'en': {
        # === LỖI CHUNG ===
        'db_error': "❌ Database error. Please try again later.",
        'min_amount_100': "❌ Minimum amount is 100.",
        'not_enough_fund': "❌ You do not have enough Fund.",
        'not_enough_coupon': "❌ You do not have enough Coupon.",
        'not_enough_currency': "❌ You do not have enough {currency_name} to bet.",
        'generic_error': "❌ An error occurred: {error}",

        # === LỆNH ADMIN ===
        'admin_buff_gt_zero': "❌ Amount must be greater than 0.",
        'admin_buff_success': "✅ Added **{amount:,}** {currency_key} to {member_mention}.",
        'admin_not_owner': "⛔ This command is for the Bot Owner only.",
        'setup_config_error': "❌ Configuration error: Please replace placeholder IDs in ROLE_IDS.",
        'setup_setting_up': "Setting up...",
        'setup_success': "✅ Successfully set up! Please pin this message.",
        'setup_error': "❌ Error: The bot could not send a message or add reactions.",

        # === LỆNH NGÔN NGỮ ===
        'lang_changed_success': "✅ Your language has been changed to English.",

        # === LỆNH LEADERBOARD ===
        'lb_db_not_ready': "❌ Error: Database is not ready.",
        'lb_query_error': "❌ An error occurred while querying the leaderboard.",
        'lb_hero_title': "🏆 Hero Leaderboard - {rank_name}",
        'lb_hero_desc': "Top 10 players with the highest Level and XP in {rank_name}.",
        'lb_monster_title': "🏆 Monster Leaderboard - {rank_name}",
        'lb_monster_desc': "Top 10 monsters with the highest Level and XP in {rank_name}.",
        'lb_no_players': "No players found at this rank.",
        'lb_user_id': "User ID: {id}",

        # === HỆ THỐNG LEVEL (DM) ===
        'level_up_dm': (
            "🎉 Congratulations {mention}! You have leveled up to **Level {new_level}**!\n"
            "🎁 Level Up Reward: **+{reward_fund:,}** {fund_emoji} Fund and **+{reward_coupon:,}** {coupon_emoji} Coupon!"
        ),
        'rank_up_dm': "🌟 You have been promoted to **{new_role_name}** rank!",

        # === LỆNH NGƯỜI DÙNG ===
        # /profile
        'profile_title': "👤 {name}'s Profile",
        'profile_group': "📜 Group",
        'profile_no_group': "Not selected",
        'profile_level': "⭐ Level",
        'profile_rank': "🏆 Rank",
        'profile_no_rank': "No rank",
        'profile_xp': "📈 XP",
        'profile_fund': "💰 Fund",
        'profile_coupon': "🎟️ Coupon",
        
        # /daily
        'daily_already': "⏳ You have already claimed your daily reward today!",
        'daily_success': "✅ Daily reward claimed! You received:\n**+{fund_reward:,}** {fund_emoji} & **+{coupon_reward:,}** {coupon_emoji}",

        # /exchange
        'exchange_min_amount': "❌ Minimum exchange amount is 100.",
        'exchange_not_enough': "❌ You do not have enough {source_name}.",
        'exchange_success': "✅ Exchanged **{amount:,}** {source_name} for {target_name}.",

        # /all_in
        'all_in_title': "🎲 ALL IN - Bet {currency_name}",
        'all_in_description': "{mention} is betting **{bet_amount:,}** {currency_emoji}...",
        'all_in_result': "Result",
        'all_in_win_lucky': "🎉 **BIG WIN!** You hit **x{multiplier}** your bet!",
        'all_in_lose_normal': "💀 **BET LOST!** You lost your bet.",
        'all_in_lose_heavy': "💀 **HEAVY LOSS!** You were fined x{loss_multiplier:.1f} your bet!",
        'all_in_lose_all': "💀 **BET LOST!** You lost **EVERYTHING** (hit x{loss_multiplier:.1f} but were capped)!",
        'all_in_bet_currency': "Currency Bet",
        'all_in_bet_amount': "Amount Bet",
        'all_in_profit_loss': "Profit/Loss",
        'all_in_old_balance': "Old Balance",
        'all_in_new_balance': "New Balance",

        # /transfer
        'transfer_self': "❌ You cannot transfer to yourself.",
        'transfer_success': "✅ Transferred **{amount:,}** {currency_key} to {recipient_mention}.",
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
