import telebot, re, os, json, time
from flask import Flask
from threading import Thread, Lock

# --- 1. SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  

# threaded=True ቦቱ ብዙ ሰው እንዲያስተናግድ ያደርጋል
bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=20)
app = Flask(__name__)
db_lock = Lock() # ዳታው እንዳይጋጭ መቆለፊያ

# --- 2. DATA STRUCTURE ---
data = {
    "config": {"db_msg_id": None},
    "boards": {
        "1": {"name": "ሰሌዳ 1 (1-100)", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 20},
        "2": {"name": "ሰሌዳ 2 (1-50)", "max": 50, "active": False, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 10},
        "3": {"name": "ሰሌዳ 3 (1-25)", "max": 25, "active": False, "slots": {}, "msg_id": None, "prizes": [100, 50, 20], "price": 5}
    },
    "users": {}
}

# --- 3. DATABASE ENGINE ---
def save_db():
    with db_lock:
        try:
            payload = "💾 DB_STORAGE " + json.dumps(data)
            db_id = data["config"].get("db_msg_id")
            if db_id: 
                bot.edit_message_text(payload, DB_CHANNEL_ID, db_id)
            else:
                m = bot.send_message(DB_CHANNEL_ID, payload)
                data["config"]["db_msg_id"] = m.message_id
        except Exception as e:
            print(f"Save error: {e}")

def load_db():
    try:
        msgs = bot.get_chat_history(DB_CHANNEL_ID, limit=10)
        for m in msgs:
            if m.text and "💾 DB_STORAGE" in m.text:
                json_str = m.text.replace("💾 DB_STORAGE", "").strip()
                loaded = json.loads(json_str)
                data.update(loaded)
                return True
    except Exception as e:
        print(f"Load error: {e}")
    return False

# --- 4. UI ENGINE ---
def refresh_group(bid, new=False):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    txt = f"🔥 **{b['name']}** {status}\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{b['price']} ETB` | 🎁 **ሽልማት:** `{sum(b['prizes'])} ETB` \n━━━━━━━━━━━━━\n"
    
    for i in range(1, b["max"] + 1):
        n = str(i)
        if n in b["slots"]:
            txt += f"{i:02d}.{b['slots'][n]['name'][:4]}🏆 "
        else:
            txt += f"{i:02d}.⚪️ "
        if i % 4 == 0: txt += "\n" # ለሞባይል እይታ በ 4 ተደርጓል
    
    txt += f"\n💰 🥇{b['prizes'][0]} | 🥈{b['prizes'][1]} | 🥉{b['prizes'][2]}\n━━━━━━━━━━━━━\n🕹 @fasil_assistant_bot"
    
    try:
        if new or not b.get("msg_id"):
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
    if uid not in data["users"]:
        data["users"][uid] = {"tks": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    
    kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]:
            kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} - ({v['price']} ETB)", callback_data=f"start_sel_{k}"))
    
    main_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    main_kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ እጣ")
    if int(uid) == ADMIN_ID: main_kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, f"🌟 **እንኳን ወደ ፋሲል ልዩ ዕጣ በሰላም መጡ!** 🌟", reply_markup=main_kb, parse_mode="Markdown")
    bot.send_message(uid, "👇 ሰሌዳ እዚህ ይምረጡ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    if uid not in data["users"]:
        data["users"][uid] = {"tks": 0, "name": c.from_user.first_name, "step": "", "sel_bid": None}
    u = data["users"][uid]

    if c.data.startswith("start_sel_"):
        bid = c.data.split("_")[-1]
        u["sel_bid"] = bid
        bot.edit_message_text(f"✅ ሰሌዳ {bid} ተመርጧል! እባክዎ ደረሰኝ ይላኩ።", uid, c.message.message_id)

    elif c.data.startswith("n_"):
        bid = u.get("sel_bid")
        n = c.data.split("_")[1]
        if bid and u["tks"] > 0:
            with db_lock:
                if n not in data["boards"][bid]["slots"]:
                    data["boards"][bid]["slots"][n] = {"name": u["name"], "id": uid}
                    u["tks"] -= 1
                    bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል!")
                    refresh_group(bid)
                    bot.delete_message(uid, c.message.message_id)
                else:
                    bot.answer_callback_query(c.id, "⚠️ ተይዟል!", show_alert=True)
        else:
            bot.answer_callback_query(c.id, "❌ እጣ የለዎትም!", show_alert=True)

    elif c.data.startswith("ok_") and int(uid) == ADMIN_ID:
        _, t_uid, _, bid = c.data.split("_")
        data["users"][t_uid]["tks"] += 1
        data["users"][t_uid]["step"] = "ASK_NAME"
        bot.send_message(t_uid, "✅ ደረሰኝዎ ጸድቋል! አሁን ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)
        save_db()

@bot.message_handler(content_types=['text', 'photo'])
def handle_msgs(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: return
    u = data["users"][uid]

    if u['step'] == "ASK_NAME":
        u['name'] = m.text; u['step'] = ""; save_db()
        bot.send_message(uid, "✅ ተመዝግቧል! አሁን '🕹 ቁጥር ምረጥ' ይጫኑ።")
        return

    if m.text == "🕹 ቁጥር ምረጥ":
        bid = u.get("sel_bid")
        if u['tks'] > 0 and bid:
            b = data["boards"][bid]
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
            kb.add(*btns)
            bot.send_message(uid, "🔢 ቁጥር ይምረጡ፦", reply_markup=kb)
        else:
            bot.send_message(uid, "❌ እጣ የለዎትም ወይም ሰሌዳ አልመረጡም።")

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        kb.add(telebot.types.InlineKeyboardButton("♻️ ሰሌዳ አጽዳ (Reset)", callback_data="adm_reset_main"),
               telebot.types.InlineKeyboardButton("🟢/🔴 ሰሌዳ ክፈት/ዝጋ", callback_data="adm_toggle_main"))
        bot.send_message(uid, "🛠 **Admin Menu**", reply_markup=kb)

    elif m.content_type == 'photo' or (m.text and len(m.text) > 10):
        bid = u.get("sel_bid")
        if not bid: return
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_0_{bid}"))
        bot.send_message(uid, "⏳ ደረሰኝ ተልኳል...")
        if m.content_type == 'photo':
            bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"ደረሰኝ ከ {u['name']}", reply_markup=kb)
        else:
            bot.send_message(ADMIN_ID, f"SMS: {m.text}", reply_markup=kb)

# --- 6. SERVER & RUN ---
@app.route('/')
def home(): return "Bot Running"

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    print("Bot is starting...")
    bot.polling(non_stop=True, skip_pending=True)
