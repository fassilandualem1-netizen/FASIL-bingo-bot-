import telebot
import re
import os
import json
import time
from flask import Flask
from threading import Thread

# --- 1. ዋና ቅንብሮች (Configuration) ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 2. ዳታ አያያዝ (Data Storage) ---
data = {
    "game": {"price": 20, "board": {}, "msg_id": None, "prizes": [500, 300, 100], "db_msg_id": None},
    "users": {}
}

def load_db():
    """መረጃን ከቻናሉ ላይ መጫኛ"""
    try:
        msgs = bot.get_chat_history(DB_CHANNEL_ID, limit=10)
        for m in msgs:
            if "💾 DB_STORAGE" in m.text:
                json_str = m.text.replace("💾 DB_STORAGE", "").strip()
                loaded = json.loads(json_str)
                data["game"] = loaded["game"]
                data["users"] = loaded["users"]
                print("✅ Database Synchronized")
                return
    except: print("⚠️ Starting with fresh database")

def save_db():
    """መረጃን ወደ ቻናሉ መላኪያ (Backup)"""
    try:
        payload = "💾 DB_STORAGE " + json.dumps(data)
        db_id = data["game"].get("db_msg_id")
        if db_id: bot.edit_message_text(payload, DB_CHANNEL_ID, db_id)
        else:
            m = bot.send_message(DB_CHANNEL_ID, payload)
            data["game"]["db_msg_id"] = m.message_id
    except: print("❌ Sync Error")

# --- 3. የሰሌዳ ዲዛይን (Board Design) ---
def draw_board():
    g = data["game"]
    b, p = g["board"], g["prizes"]
    txt = f"🔥 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🔥\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{g['price']} ETB` | 🎁 **ሽልማት:** `{sum(p)} ETB` \n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        n = str(i)
        if n in b: txt += f"{i:02d}.{b[n]['name'][:5]}🏆 "
        else: txt += f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    txt += f"\n💰 **የሽልማት ዝርዝር፦**\n🥇 1ኛ: `{p[0]} ETB` | 🥈 2ኛ: `{p[1]} ETB` | 🥉 3ኛ: `{p[2]} ETB`\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n"
    txt += f"🕹 ለመሳተፍ፦ @fasil_assistant_bot"
    return txt

def refresh_group(new=False):
    txt, g = draw_board(), data["game"]
    try:
        if new or not g["msg_id"]:
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            g["msg_id"] = m.message_id
            bot.pin_chat_message(GROUP_ID, m.message_id)
        else: bot.edit_message_text(txt, GROUP_ID, g["msg_id"], parse_mode="Markdown")
    except: pass
    save_db()

# --- 4. መልዕክት ተቀባይ (Message Handlers) ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"tks": 0, "name": m.from_user.first_name, "step": ""}
    
    welcome_msg = (
        f"👋 **ሰላም {m.from_user.first_name}! እንኳን መጡ!** 🎰\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **የአሁኑ መደብ:** `{data['game']['price']} ETB`\n"
        f"🎫 **የእርስዎ ቀሪ እጣ:** `{data['users'][uid]['tks']} እጣ` \n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 **የንግድ ባንክ (CBE):**\n`1000584461757` (ፋሲል)\n\n"
        f"📱 **ቴሌብር (Telebirr):**\n`0951381356` \n\n"
        f"📩 **ክፍያውን ከፈጸሙ በኋላ የደረሰኙን SMS እዚህ ይላኩ።**"
    )
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ እጣ")
    if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
    bot.send_message(uid, welcome_msg, reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    uid = str(c.from_user.id)
    # ማጽደቅ
    if c.data.startswith("ok_"):
        _, t_uid, amt = c.data.split("_")
        tks = int(float(amt) // data["game"]["price"])
        if t_uid not in data["users"]: data["users"][t_uid] = {"tks": 0, "name": "Player", "step": ""}
        data["users"][t_uid]["tks"] += tks
        data["users"][t_uid]["step"] = "ASK_NAME"
        bot.send_message(t_uid, f"✅ **ደረሰኝዎ ጸድቋል!** {tks} እጣ ተሰጥቶዎታል።\nእባክዎ ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)
        save_db()
    # ውድቅ ማድረግ
    elif c.data.startswith("no_"):
        bot.send_message(c.data.split("_")[1], "❌ ደረሰኝዎ ውድቅ ተደርጓል። እባክዎ ትክክለኛ ደረሰኝ ይላኩ።")
        bot.delete_message(ADMIN_ID, c.message.message_id)
    # ቁጥር መያዝ
    elif c.data.startswith("n_"):
        n = c.data.split("_")[1]
        if data["users"][uid]["tks"] > 0:
            data["game"]["board"][n] = {"name": data["users"][uid]["name"], "id": uid}
            data["users"][uid]["tks"] -= 1
            refresh_group()
            bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል!")
        else: bot.answer_callback_query(c.id, "❌ ቀድመው እጣ ይግዙ!", show_alert=True)
    # አድሚን ተግባራት
    elif c.data == "adm_price": data["users"][uid]["step"] = "SET_PRICE"; bot.send_message(uid, "💰 አዲስ ዋጋ ይጻፉ፦")
    elif c.data == "adm_prizes": data["users"][uid]["step"] = "SET_PRIZES"; bot.send_message(uid, "🏆 ሽልማቶችን በኮማ ይጻፉ (ምሳሌ: 500,300,100)፦")
    elif c.data == "adm_reset":
        data["game"]["board"] = {}
        refresh_group(new=True)
        bot.answer_callback_query(c.id, "♻️ ሰሌዳው ጸድቷል!")

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private_chats(m):
    uid = str(m.from_user.id)
    u = data["users"].get(uid, {"tks": 0, "name": m.from_user.first_name, "step": ""})
    
    if u['step'] == "ASK_NAME":
        u['name'] = m.text; u['step'] = ""; save_db()
        bot.send_message(uid, f"✅ ተመዝግቧል! አሁን '🕹 ቁጥር ምረጥ' ይጫኑ።")
    elif u['step'] == "SET_PRICE" and int(uid) == ADMIN_ID:
        data["game"]["price"] = int(m.text); u['step'] = ""; save_db()
        bot.send_message(uid, "✅ ዋጋ ተቀይሯል!")
    elif u['step'] == "SET_PRIZES" and int(uid) == ADMIN_ID:
        try:
            data["game"]["prizes"] = [int(x.strip()) for x in m.text.split(',')]
            u['step'] = ""; save_db(); refresh_group()
            bot.send_message(uid, "✅ ሽልማት ተቀምጧል!")
        except: bot.send_message(uid, "❌ ስህተት! (ምሳሌ: 500,300,100)")
    
    elif m.text == "🕹 ቁጥር ምረጥ":
        if u['tks'] <= 0: bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ።")
        else:
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            kb.add(*[telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in data["game"]["board"]])
            bot.send_message(uid, "🔢 ቁጥር ይምረጡ፦", reply_markup=kb)
    elif m.text == "🎫 የእኔ እጣ":
        bot.send_message(uid, f"👤 ስም: {u['name']}\n🎟 ቀሪ እጣ: {u['tks']}")
    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="adm_price"), telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="adm_prizes"))
        kb.add(telebot.types.InlineKeyboardButton("♻️ ሰሌዳ አጽዳ", callback_data="adm_reset"))
        bot.send_message(uid, "🛠 Admin Panel", reply_markup=kb)
    elif re.search(r"(FT|DCA|[0-9]{10})", m.text):
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_20"), telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 ደረሰኝ ከ {m.from_user.first_name}:\n`{m.text}`", reply_markup=kb, parse_mode="Markdown")
        bot.send_message(uid, "📩 ደረሰኝ ተልኳል፣ እስኪረጋገጥ ይጠብቁ።")

# --- 5. አጀማመር (Start Server) ---
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
