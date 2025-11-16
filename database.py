import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Import file config
import config

# Biến db toàn cục
db = None

def initialize_firestore():
    """Khởi tạo Firebase Admin SDK sử dụng biến môi trường."""
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
    """Lấy dữ liệu người dùng từ Firestore."""
    global db
    if db is None:
        initialize_firestore() 
        if db is None:
            return None 

    # Dùng biến từ config.py
    doc_ref = db.collection(config.COLLECTION_NAME).document(str(user_id))
    try:
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            
            # (Copy y hệt phần xử lý datetime từ file cũ của bạn)
            if data.get('last_xp_message') and isinstance(data['last_xp_message'], firestore.client.datetime):
                data['last_xp_message'] = data['last_xp_message'].replace(tzinfo=None)
            elif not data.get('last_xp_message'):
                 data['last_xp_message'] = datetime.min
            
            if data.get('last_daily') and isinstance(data['last_daily'], firestore.client.datetime):
                data['last_daily'] = data['last_daily'].replace(tzinfo=None)
            elif not data.get('last_daily'):
                data['last_daily'] = None
                
            return data
        else:
            # Tạo dữ liệu mặc định
            return {
                'xp': 0,
                'level': 0,
                'fund': 0,
                'coupon': 0,
                'role_group': None,
                'last_daily': None,
                'last_xp_message': datetime.min,
            }
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

    # Dùng biến từ config.py
    doc_ref = db.collection(config.COLLECTION_NAME).document(str(user_id))
    try:
        doc_ref.set(data)
    except Exception as e:
        print(f"❌ Lỗi khi lưu dữ liệu cho user {user_id}: {e}")
        db = None # Thử reset db connection nếu lỗi

async def get_reaction_message_ids():
    """Lấy Message ID của tin nhắn Reaction Role từ Firestore."""
    if db is None: return {}
    # Dùng biến từ config.py
    doc_ref = db.collection(config.CONFIG_COLLECTION).document(config.CONFIG_DOC_ID)
    try:
        doc = doc_ref.get()
        return doc.to_dict().get('messages', {}) if doc.exists else {}
    except Exception as e:
        print(f"❌ Lỗi khi lấy cấu hình Reaction Role: {e}")
        return {}

async def save_reaction_message_id(guild_id, message_id, channel_id):
    """Lưu Message ID của tin nhắn Reaction Role vào Firestore."""
    if db is None: return
    # Dùng biến từ config.py
    doc_ref = db.collection(config.CONFIG_COLLECTION).document(config.CONFIG_DOC_ID)
    try:
        @firestore.transactional
        def update_config_transaction(transaction):
            snapshot = doc_ref.get(transaction=transaction)
            config_data = snapshot.to_dict() or {'messages': {}}
            config_data['messages'][str(guild_id)] = {
                'message_id': str(message_id),
                'channel_id': str(channel_id)
            }
            transaction.set(doc_ref, config_data)
        
        transaction = db.transaction()
        update_config_transaction(transaction)
    except Exception as e:
        print(f"❌ Lỗi khi lưu cấu hình Reaction Role: {e}")
