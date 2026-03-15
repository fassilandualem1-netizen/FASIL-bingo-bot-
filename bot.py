import telebot, re, os, json, time
from flask import Flask
from threading import Thread

# --- 1. SETUP (ምንም እንዳይቀየር) ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 2. DATA STRUCTURE ---
data = {
    "config": {"price": 20, "db_msg_id": None},
    "boards": {
        "1": {"name": "ሰሌዳ 1 (1-100)", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100]},
        "2": {"name": "ሰሌዳ 2 (1-50)", "max": 50, "active": False, "slots": {}, "msg_id": None, "prizes": [250, 150, 50]},
        "3": {"name": "ሰሌዳ 3 (1-20)", "max": 20, "active": False, "slots": {}, "msg_id": None, "prizes": [100, 50, 20]}
    },
    "users": {}
}

# --- 3. DATABASE ENGINE (The Secure Part) ---
def save_db():
    """ሁሉንም ዳታ ወደ ቻናል መላኪያ"""
    try:
        payload = "💾 DB_STORAGE " + json.dumps(data)
        db_id = data["config"].get("db_msg_id")
        if db_id:
            bot.edit_message_text(payload, DB_CHANNEL_ID, db_id)
        else:
            m = bot.send_message(DB_CHANNEL_ID, payload)
            data["config"]["db_msg_id"] = m.message_id
    except Exception as e:
        print(f"❌ Save Error: {e}")

def load_db():
    """ቦቱ ሲነሳ ዳታውን ከቻናል መጫኛ"""
    try:
        msgs = bot.get_chat_history(DB_CHANNEL_ID, limit=10)
        for m in msgs:
            if m.text and "💾 DB_STORAGE" in m.text:
                clean_json = m.text.replace("💾 DB_STORAGE", "").strip()
                loaded_data = json.loads(clean_json)
                # አስፈላጊዎቹን ክፍሎች መተካት
                data["config"] = loaded_data.get("config", data["config"])
                data["boards"] = loaded_data.get("boards", data["boards"])
                data["users"] = loaded_data.get("users", data["users"])
                print("✅ Database successfully synced from Channel!")
                return True
    except Exception as e:
        print(f"⚠️ Load Error: {e}")
    return False

# --- 4. BOARD DRAWING ---
def draw_board(bid):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    txt = f"🔥 **{b['name']}** {status}\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{data['config']['price']} ETB` | 🎁 **ሽልማት:** `{sum(b['prizes'])}` \n━━━━━━━━━━━━━\n"
    for i in range(1, b["max"] + 1):
        n = str(i)
        txt += f"{i:02d}.{b['slots'][n]['name'][:4]}🏆 " if n in b["slots"] else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    txt += f"\n💰 🥇{b['prizes'][0]} | 🥈{b['prizes'][1]} | 🥉{b['prizes'][2]}\n━━━━━━━━━━━━━\n🕹 @fasil_assistant_bot"
    return txt

def refresh_group(bid, new=False):
    b, txt = data["boards"][bid], draw_board(bid)
    try:
        if new or not b["msg_id"]:
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            b["msg_id"] = m.message_id
            bot.pin_chat_message(GROUP_ID, m.message_id)
        else:
            bot.edit_message_text(txt, GROUP_ID, b["msg_id"], parse_mode="Markdown")
    except: pass
    save_db()

# --- 5. HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"tks": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    
    msg = (f"👋 ሰላም {m.from_user.first_name}!\n"
           f"💰 መደብ፦ `{data['config']['price']} ETB` | እጣዎ፦ `{data['users'][uid]['tks']}`\n"
           f"🏦 CBE: `1000584461757` | 📱 Telebirr: `0951381356` \n"
           f"━━━━━━━━━━━━━\n📩 ደረሰኝ (SMS ወይም ፎቶ) እዚህ ይላኩ።")
    
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ እጣ")
    if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
    bot.send_message(uid, msg, reply_markup=kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid = str(c.from_user.id)
    # ማጽደቅ
    if c.data.startswith("ok_"):
        _, t_uid, amt = c.data.split("_")
        tks = int(float(amt) // data["config"]["price"])
        if t_uid not in data["users"]: data["users"][t_uid] = {"tks": 0, "name": "Player", "step": ""}
        data["users"][t_uid]["tks"] += tks
        data["users"][t_uid]["step"] = "ASK_NAME"
        bot.send_message(t_uid, f"✅ ጸድቋል! {tks} እጣ ተጨምሯል። ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id); save_db()

    # ሰሌዳ መምረጥ
    elif c.data.startswith("sel_"):
        bid = c.data.split("_")[1]
        if data["boards"][bid]["active"]:
            data["users"][uid]["sel_bid"] = bid
            b = data["boards"][bid]
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
            kb.add(*btns)
            bot.edit_message_text(f"🔢 {b['name']} ቁጥር ይምረጡ፦", uid, c.message.message_id, reply_markup=kb)
        else: bot.answer_callback_query(c.id, "⚠️ ይሄ ሰሌዳ ዝግ ነው!", show_alert=True)

    # ቁጥር መያዝ
    elif c.data.startswith("n_"):
        bid = data["users"][uid].get("sel_bid")
        n = c.data.split("_")[1]
        if bid and data["users"][uid]["tks"] > 0:
            data["boards"][bid]["slots"][n] = {"name": data["users"][uid]["name"], "id": uid}
            data["users"][uid]["tks"] -= 1
            refresh_group(bid); bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል!")
            try: bot.delete_message(uid, c.message.message_id)
            except: pass
        else: bot.answer_callback_query(c.id, "❌ እጣ የለዎትም!", show_alert=True)

    # አድሚን On/Off
    elif c.data.startswith("tog_") and int(uid) == ADMIN_ID:
        bid = c.data.split("_")[1]
        data["boards"][bid]["active"] = not data["boards"][bid]["active"]
        refresh_group(bid, new=True); bot.answer_callback_query(c.id, "ሁኔታው ተቀይሯል!")

@bot.message_handler(content_types=['text', 'photo'])
def handle_all(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"tks": 0, "name": m.from_user.first_name, "step": ""}
    u = data["users"][uid]

    if m.text == "🕹 ቁጥር ምረጥ":
        if u['tks'] <= 0: bot.send_message(uid, "❌ እጣ የለዎትም። መጀመሪያ ደረሰኝ ይላኩ።")
        else:
            kb = telebot.types.InlineKeyboardMarkup(row_width=1)
            for k, v in data["boards"].items():
                status = "🟢" if v["active"] else "🔴"
                kb.add(telebot.types.InlineKeyboardButton(f"{status} {v['name']}", callback_data=f"sel_{k}"))
            bot.send_message(uid, "የትኛው ሰሌዳ ላይ መሳተፍ ይፈልጋሉ?", reply_markup=kb)

    elif u['step'] == "ASK_NAME":
        u['name'] = m.text; u['step'] = ""; save_db()
        bot.send_message(uid, "✅ ተመዝግቧል! አሁን '🕹 ቁጥር ምረጥ' ይጫኑ።")

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup()
        for k, v in data["boards"].items():
            kb.add(telebot.types.InlineKeyboardButton(f"On/Off {v['name']}", callback_data=f"tog_{k}"))
        bot.send_message(uid, "🛠 የሰሌዳዎች መቆጣጠሪያ፦", reply_markup=kb)

    elif m.content_type == 'photo' or (m.text and re.search(r"(FT|DCA|[0-9]{10})", m.text)):
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_20"), 
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
        if m.content_type == 'photo':
            bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 ፎቶ ደረሰኝ ከ {m.from_user.first_name}", reply_markup=kb)
        else:
            bot.send_message(ADMIN_ID, f"📩 SMS ደረሰኝ ከ {m.from_user.first_name}:\n`{m.text}`", reply_markup=kb, parse_mode="Markdown")
        bot.send_message(uid, "📩 ደረሰኝ ተልኳል፣ አድሚን እስኪያጸድቅ ይጠብቁ።")

# --- 6. SERVER ---
@app.route('/')
def home(): return "OK"

if __name__ == "__main__":
    # ቻናሉን ቼክ አድርጎ ዳታ መጫን (ይህ በጣም አስፈላጊው ክፍል ነው!)
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
