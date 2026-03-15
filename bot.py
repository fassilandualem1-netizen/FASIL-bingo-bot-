import telebot
import re
import os
import json
import time
from flask import Flask
from threading import Thread

# --- 1. SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  # አንተ የላክኸው የቻናል ID

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 2. FAST CACHE (In-Memory Data) ---
# ቦቱ ሲነሳ መረጃውን ከቻናሉ ይጭነዋል
data = {
    "game": {"price": 20, "board": {}, "msg_id": None, "prizes": [0,0,0], "db_msg_id": None},
    "users": {}
}

# --- 3. TELEGRAM DATABASE ENGINE ---
def load_db():
    """ከቻናሉ ላይ መረጃውን ያነባል"""
    try:
        # በቻናሉ ውስጥ ያሉትን የመጨረሻ መልዕክቶች ይፈትሻል
        msgs = bot.get_chat_history(DB_CHANNEL_ID, limit=10)
        for m in msgs:
            if "💾 DB_STORAGE" in m.text:
                json_str = m.text.replace("💾 DB_STORAGE", "").strip()
                loaded = json.loads(json_str)
                data["game"] = loaded["game"]
                data["users"] = loaded["users"]
                print("✅ Database Loaded from Channel")
                return
    except Exception as e:
        print(f"⚠️ DB Load Warning: {e}")

def save_db():
    """መረጃውን ወደ ቻናሉ ይልካል"""
    try:
        payload = "💾 DB_STORAGE " + json.dumps(data)
        db_id = data["game"].get("db_msg_id")
        
        if db_id:
            bot.edit_message_text(payload, DB_CHANNEL_ID, db_id)
        else:
            m = bot.send_message(DB_CHANNEL_ID, payload)
            data["game"]["db_msg_id"] = m.message_id
    except Exception as e:
        print(f"❌ DB Save Error: {e}")

# --- 4. BOARD LOGIC ---
def draw_board():
    g = data["game"]
    b, p = g["board"], g["prizes"]
    txt = f"🔥 **የፋሲል ዕጣ ልዩ ሰሌዳ** 🔥\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{g['price']} ETB` | 🎁 **ሽልማት:** `{sum(p)}` \n━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        n = str(i)
        txt += f"{i:02d}.{b[n]['name'][:5]}🏆 " if n in b else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    txt += f"\n💰 🥇{p[0]} | 🥈{p[1]} | 🥉{p[2]}\n━━━━━━━━━━━━━\n🕹 @Fasil_assistant_bot"
    return txt

def refresh_group(new=False):
    txt = draw_board()
    g = data["game"]
    try:
        if new or not g["msg_id"]:
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            g["msg_id"] = m.message_id
            bot.pin_chat_message(GROUP_ID, m.message_id)
        else:
            bot.edit_message_text(txt, GROUP_ID, g["msg_id"], parse_mode="Markdown")
    except: pass
    save_db() # ማንኛውም ለውጥ ሲኖር Backup ያደርጋል

# --- 5. HANDLERS ---
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(c):
    uid = str(c.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"tks": 0, "name": "Player", "step": ""}
    
    # ደረሰኝ ማጽደቅ
    if c.data.startswith("ok_"):
        _, t_uid, amt = c.data.split("_")
        tks = int(float(amt) // data["game"]["price"])
        if t_uid not in data["users"]: data["users"][t_uid] = {"tks": 0, "name": "Player", "step": ""}
        data["users"][t_uid]["tks"] += tks
        data["users"][t_uid]["step"] = "ASK_NAME"
        bot.send_message(t_uid, f"✅ ጸድቋል! {tks} እጣ አለዎት። ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)
        save_db()

    # ቁጥር መምረጥ
    elif c.data.startswith("n_"):
        n = c.data.split("_")[1]
        if data["users"][uid]["tks"] > 0:
            data["game"]["board"][n] = {"name": data["users"][uid]["name"], "id": uid}
            data["users"][uid]["tks"] -= 1
            refresh_group()
            bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል!")
        else:
            bot.answer_callback_query(c.id, "❌ እጣ የለዎትም!", show_alert=True)

    # አድሚን ሪሴት
    elif c.data == "adm_reset" and int(uid) == ADMIN_ID:
        data["game"]["board"] = {}
        refresh_group(new=True)
        bot.answer_callback_query(c.id, "ሰሌዳው ታድሷል!")

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"tks": 0, "name": "Player", "step": ""}

    if m.text == "/start":
        kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ እጣ")
        if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
        bot.send_message(uid, f"👋 ሰላም! መደብ: {data['game']['price']} ETB\nደረሰኝ እዚህ ይላኩ 👇", reply_markup=kb)

    elif data["users"][uid]["step"] == "ASK_NAME":
        data["users"][uid]["name"] = m.text
        data["users"][uid]["step"] = ""
        bot.send_message(uid, "✅ ተመዝግቧል! አሁን ቁጥር ይምረጡ።")
        save_db()

    elif m.text == "🕹 ቁጥር ምረጥ":
        if data["users"][uid]["tks"] <= 0:
            bot.send_message(uid, "❌ መጀመሪያ ደረሰኝ በመላክ እጣ ይግዙ።")
        else:
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            kb.add(*[telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in data["game"]["board"]])
            bot.send_message(uid, "እባክዎ ቁጥር ይምረጡ፦", reply_markup=kb)

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="adm_reset"))
        bot.send_message(uid, "🛠 አድሚን መቆጣጠሪያ፦", reply_markup=kb)

    elif re.search(r"(FT|DCA|[0-9]{10})", m.text):
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_20"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 ደረሰኝ ከ {m.from_user.first_name}:\n{m.text}", reply_markup=kb)
        bot.send_message(uid, "📩 ደረሰኝ ተልኳል፣ አድሚን እስኪያጸድቅ ይጠብቁ።")

# --- 6. RUN ---
@app.route('/')
def home(): return "OK"

if __name__ == "__main__":
    load_db() # ሲነሳ ዳታ መጫን
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
