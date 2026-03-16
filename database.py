# database.py
import json
import config

data = {
    "config": {"db_msg_id": None},
    "boards": {
        "1": {"name": "ሰሌዳ 1", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 50},
        "2": {"name": "ሰሌዳ 2", "max": 50, "active": True, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 20}
    },
    "users": {}
}

def save_db(bot):
    try:
        payload = "💾 DB_STORAGE " + json.dumps(data)
        db_id = data["config"].get("db_msg_id")
        if db_id: 
            bot.edit_message_text(payload, config.DB_CHANNEL_ID, db_id)
        else:
            m = bot.send_message(config.DB_CHANNEL_ID, payload)
            data["config"]["db_msg_id"] = m.message_id
            bot.pin_chat_message(config.DB_CHANNEL_ID, m.message_id)
    except: pass

def load_db(bot):
    try:
        chat = bot.get_chat(config.DB_CHANNEL_ID)
        if chat.pinned_message and "💾 DB_STORAGE" in chat.pinned_message.text:
            raw = chat.pinned_message.text.replace("💾 DB_STORAGE", "").strip()
            data.update(json.loads(raw))
            return True
    except: pass
    return False
