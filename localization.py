# File này chứa tất cả các chuỗi văn bản cho bot
LANG_STRINGS = {
    'vi': {
        # Lỗi chung
        'db_error': "❌ Lỗi cơ sở dữ liệu. Vui lòng thử lại sau.",
        'min_amount_100': "❌ Số tiền tối thiểu là 100.",
        'not_enough_fund': "❌ Bạn không đủ Fund.",
        'not_enough_coupon': "❌ Bạn không đủ Coupon.",
        
        # Lệnh /daily
        'daily_already': "⏳ Bạn đã điểm danh hôm nay rồi!",
        'daily_success': "✅ Điểm danh thành công! Nhận được:\n**+{fund_reward:,}** {fund_emoji} & **+{coupon_reward:,}** {coupon_emoji}",

        # Lệnh /profile
        'profile_title': "👤 Hồ sơ của {name}",
        'profile_group': "📜 Nhóm",
        'profile_no_group': "Chưa chọn",
        'profile_level': "⭐ Level",
        'profile_rank': "🏆 Rank",
        'profile_no_rank': "Chưa có",
        'profile_xp': "📈 XP",
        'profile_fund': "💰 Fund",
        'profile_coupon': "🎟️ Coupon",
        
        # Lệnh /language
        'lang_changed_success': "✅ Ngôn ngữ của bạn đã được đổi thành Tiếng Việt.",

        # (Bạn cần tự thêm các chuỗi khác cho /all_in, /exchange, /transfer, v.v.)
    },
    'en': {
        # Lỗi chung
        'db_error': "❌ Database error. Please try again later.",
        'min_amount_100': "❌ Minimum amount is 100.",
        'not_enough_fund': "❌ You do not have enough Fund.",
        'not_enough_coupon': "❌ You do not have enough Coupon.",

        # Lệnh /daily
        'daily_already': "⏳ You have already claimed your daily reward today!",
        'daily_success': "✅ Daily reward claimed! You received:\n**+{fund_reward:,}** {fund_emoji} & **+{coupon_reward:,}** {coupon_emoji}",

        # Lệnh /profile
        'profile_title': "👤 {name}'s Profile",
        'profile_group': "📜 Group",
        'profile_no_group': "Not selected",
        'profile_level': "⭐ Level",
        'profile_rank': "🏆 Rank",
        'profile_no_rank': "No rank",
        'profile_xp': "📈 XP",
        'profile_fund': "💰 Fund",
        'profile_coupon': "🎟️ Coupon",

        # Lệnh /language
        'lang_changed_success': "✅ Your language has been changed to English.",

        # (You need to add other strings for /all_in, /exchange, /transfer, etc.)
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
        # Nếu không tìm thấy, trả về thông báo lỗi
        return f"⚠️ Missing string for key: '{key}' in lang: '{lang}'"

    if kwargs:
        try:
            return string_template.format(**kwargs)
        except KeyError as e:
            return f"⚠️ String format error for key '{key}': Missing {e}"
    
    return string_template
