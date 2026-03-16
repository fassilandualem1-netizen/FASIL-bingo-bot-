import telebot, re, os, json, time
from flask import Flask
from threading import Thread

# --- 1. SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 2. DATA STRUCTURE ---
data = {
    "config": {"db_msg_id": None},
    "boards": {
        "1": {"name": "ሰሌዳ 1 (20 ETB)", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 20},
        "2": {"name": "ሰሌዳ 2 (10 ETB)", "max": 50, "active": False, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 10},
        "3": {"name": "ሰሌዳ 3 (5 ETB)", "max": 25, "active": False, "slots": {}, "msg_id": None, "prizes": [100, 50, 20], "price": 5}
    },
    "users": {}
}

# --- 3. DATABASE ENGINE ---
def save_db():
    try:
        payload = "💾 DB_STORAGE " + json.dumps(data)
        db_id = data["config"].get("db_msg_id")
        if db_id: bot.edit_message_text(payload, DB_CHANNEL_ID, db_id)
        else:
            m = bot.send_message(DB_CHANNEL_ID, payload)
            data["config"]["db_msg_id"] = m.message_id
            bot.pin_chat_message(DB_CHANNEL_ID, m.message_id)
    except: pass

def load_db():
    try:
        chat = bot.get_chat(DB_CHANNEL_ID)
        if chat.pinned_message and "💾 DB_STORAGE" in chat.pinned_message.text:
            raw = chat.pinned_message.text.replace("💾 DB_STORAGE", "").strip()
            loaded = json.loads(raw)
            data.update(loaded); return True
    except: pass
    return False

# --- 4. UI ENGINE ---
def refresh_group(bid, new=False):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    txt = f"🔥 **{b['name']}** {status}\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{b['price']} ETB` | 🎁 **ሽልማት:** `{sum(b['prizes'])} ETB` \n━━━━━━━━━━━━━\n"
    for i in range(1, b["max"] + 1):
        n = str(i)
        txt += f"{i:02d}.{b['slots'][n]['name'][:4]}🏆 " if n in b["slots"] else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    txt += f"\n💰 🥇{b['prizes'][0]} | 🥈{b['prizes'][1]} | 🥉{b['prizes'][2]}\n━━━━━━━━━━━━━\n🕹 @fasil_assistant_bot"
    try:
        if new or not b["msg_id"]:
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            b["msg_id"] = m.message_id
            bot.pin_chat_message(GROUP_ID, m.message_id)
        else: bot.edit_message_text(txt, GROUP_ID, b["msg_id"], parse_mode="Markdown")
    except: pass
    save_db()

# --- 5. HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: 
        data["users"][uid] = {"tks": 0, "wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    
    # ዋና ሜኑ በተኖች
    main_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    main_kb.add("🎰 ሰሌዳ ምረጥ", "🕹 ቁጥር ምረጥ")
    main_kb.add("💰 የእኔ ዋሌት", "🎫 የእኔ እጣ")
    if int(uid) == ADMIN_ID: main_kb.add("🛠 Admin Panel")
    
    welcome_txt = (
        f"👋 **ሰላም {m.from_user.first_name}!**\n"
        f"እንኳን ወደ ፋሲል ልዩ ዕጣ ቦት በሰላም መጡ።\n\n"
        f"እባክዎ ከታች ካሉት አማራጮች አንዱን ይምረጡ።"
    )
    bot.send_message(uid, welcome_txt, reply_markup=main_kb, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    u = data["users"].get(uid)
    if not u: return

    if c.data.startswith("start_sel_"):
        bid = c.data.split("_")[-1]
        u["sel_bid"] = bid
        b = data["boards"][bid]
        txt = (
            f"✅ **{b['name']} ተመርጧል!**\n"
            f"💰 መደብ፦ `{b['price']} ETB` \n"
            f"🏦 CBE: `1000584461757` | 📱 Telebirr: `0951381356` \n"
            f"━━━━━━━━━━━━━\n"
            f"📩 እባክዎ የከፈሉበትን ደረሰኝ (ፎቶ ወይም SMS) እዚህ ይላኩ።"
        )
        bot.edit_message_text(txt, uid, c.message.message_id, parse_mode="Markdown")

    elif c.data.startswith("ok_") and int(uid) == ADMIN_ID:
        _, t_uid, amt, bid = c.data.split("_")
        amt_val = float(amt)
        price = data["boards"][bid]["price"]
        
        # ስሌት፡ ብሩን ወደ እጣ መቀየር እና ቀሪውን ዋሌት ላይ ማስቀመጥ
        tks_to_add = int(amt_val // price)
        rem_money = amt_val % price
        
        data["users"][t_uid]["tks"] += tks_to_add
        data["users"][t_uid]["wallet"] += rem_money
        data["users"][t_uid]["step"] = "ASK_NAME" if not data["users"][t_uid].get("name") else ""
        
        msg = f"✅ ደረሰኝዎ ጸድቋል!\n🎫 {tks_to_add} እጣ ተሰጥቶዎታል።"
        if rem_money > 0: msg += f"\n💰 ቀሪ {rem_money} ETB ዋሌትዎ ላይ ተቀምጧል።"
        
        bot.send_message(t_uid, msg + ("\n\nእባክዎ ስምዎን ይጻፉ፦" if data["users"][t_uid]["step"] == "ASK_NAME" else ""))
        bot.delete_message(ADMIN_ID, c.message.message_id); save_db()

    elif c.data.startswith("n_"):
        bid = u.get("sel_bid")
        n = c.data.split("_")[1]
        if bid and u["tks"] > 0:
            if n not in data["boards"][bid]["slots"]:
                data["boards"][bid]["slots"][n] = {"name": u["name"], "id": uid}
                u["tks"] -= 1
                refresh_group(bid)
                bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል!")
                bot.delete_message(uid, c.message.message_id)
            else:
                bot.answer_callback_query(c.id, "⚠️ ይቅርታ፣ ይህ ቁጥር ተይዟል!", show_alert=True)
        else:
            bot.answer_callback_query(c.id, "❌ በቂ እጣ የለዎትም!", show_alert=True)

    # ... (Other admin callbacks follow the same pattern)

@bot.message_handler(content_types=['text', 'photo'])
def handle_msgs(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: 
        data["users"][uid] = {"tks": 0, "wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    u = data["users"][uid]

    if m.text == "🎰 ሰሌዳ ምረጥ":
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        for k, v in data["boards"].items():
            if v["active"]:
                kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']}", callback_data=f"start_sel_{k}"))
        bot.send_message(uid, "እባክዎ ለመጫወት የሚፈልጉትን ሰሌዳ ይምረጡ፦", reply_markup=kb)

    elif m.text == "💰 የእኔ ዋሌት":
        bot.send_message(uid, f"💰 **የእርስዎ ቀሪ ሂሳብ፦** `{u['wallet']} ETB`", parse_mode="Markdown")

    elif m.text == "🕹 ቁጥር ምረጥ":
        bid = u.get("sel_bid")
        if u['tks'] > 0 and bid:
            b = data["boards"][bid]
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") 
                    for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
            kb.add(*btns)
            bot.send_message(uid, f"🔢 {b['name']} ቁጥር ይምረጡ፦", reply_markup=kb)
        else:
            bot.send_message(uid, "❌ በቂ እጣ የለዎትም። መጀመሪያ ሰሌዳ መርጠው ደረሰኝ ይላኩ።")

    elif m.text == "🎫 የእኔ እጣ":
        msg = f"👤 ስም፦ {u['name']}\n🎫 ቀሪ እጣዎች፦ `{u['tks']}`\n💰 ዋሌት፦ `{u['wallet']} ETB`"
        bot.send_message(uid, msg, parse_mode="Markdown")

    elif u['step'] == "ASK_NAME":
        u['name'] = m.text; u['step'] = ""; save_db()
        bot.send_message(uid, "✅ ስምዎ ተመዝግቧል! አሁን '🕹 ቁጥር ምረጥ' የሚለውን በመጫን መጫወት ይችላሉ።")

    elif m.content_type == 'photo' or (m.text and re.search(r"(FT|DCA|[0-9]{10})", m.text)):
        bid = u.get("sel_bid")
        if not bid:
            bot.send_message(uid, "⚠️ መጀመሪያ ሰሌዳ ይምረጡ (🎰 ሰሌዳ ምረጥ)")
            return
        
        price = data["boards"][bid]["price"]
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_{price}_{bid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
        
        bot.send_message(ADMIN_ID, f"📩 አዲስ ደረሰኝ ከ {m.from_user.first_name}\nሰሌዳ፦ {bid}", reply_markup=kb)
        bot.send_message(uid, "📩 ደረሰኝዎ ተልኳል። እስኪረጋገጥ ድረስ በትዕግስት ይጠብቁ።")

# --- 6. SERVER & POLLING ---
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
