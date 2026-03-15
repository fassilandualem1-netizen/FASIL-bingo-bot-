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
        "1": {"name": "ሰሌዳ 1 (1-100)", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 20},
        "2": {"name": "ሰሌዳ 2 (1-50)", "max": 50, "active": False, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 10},
        "3": {"name": "ሰሌዳ 3 (1-20)", "max": 20, "active": False, "slots": {}, "msg_id": None, "prizes": [100, 50, 20], "price": 5}
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
    except: pass

def load_db():
    try:
        msgs = bot.get_chat_history(DB_CHANNEL_ID, limit=5)
        for m in msgs:
            if m.text and "💾 DB_STORAGE" in m.text:
                loaded = json.loads(m.text.replace("💾 DB_STORAGE", "").strip())
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
    if uid not in data["users"]: data["users"][uid] = {"tks": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    
    kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]:
            kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} - ({v['price']} ETB)", callback_data=f"start_sel_{k}"))
    
    msg = f"🌟 **እንኳን ወደ ፋሲል ልዩ ዕጣ በሰላም መጡ!** 🌟\n━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "ለመጫወት መጀመሪያ መሳተፍ የሚፈልጉትን ሰሌዳ ይምረጡ፦"
    
    main_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    main_kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ እጣ")
    if int(uid) == ADMIN_ID: main_kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, msg, reply_markup=main_kb, parse_mode="Markdown")
    bot.send_message(uid, "የሚጫወቱበትን ሰሌዳ ይጫኑ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    # ሰሌዳ ምርጫ
    if c.data.startswith("start_sel_"):
        bid = c.data.split("_")[-1]
        data["users"][uid]["sel_bid"] = bid
        b = data["boards"][bid]
        bot.edit_message_text(f"✅ **{b['name']} ተመርጧል!**\n💰 መደብ፦ `{b['price']} ETB` \n🏦 CBE: `1000584461757` | 📱 Telebirr: `0951381356` \n━━━━━━━━━━━━━\n📩 እባክዎ ደረሰኝ እዚህ ይላኩ።", uid, c.message.message_id, parse_mode="Markdown")

    # አድሚን አጽድቅ/ውድቅ
    elif c.data.startswith("ok_"):
        _, t_uid, _, bid = c.data.split("_")
        data["users"][t_uid]["tks"] += 1
        data["users"][t_uid]["sel_bid"] = bid
        data["users"][t_uid]["step"] = "ASK_NAME"
        bot.send_message(t_uid, "✅ ደረሰኝዎ ጸድቋል! አሁን ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id); save_db()

    elif c.data.startswith("no_"):
        t_uid = c.data.split("_")[1]
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("💰 ብር አነስተኛ ነው", callback_data=f"rej_low_{t_uid}"),
               telebot.types.InlineKeyboardButton("❌ ደረሰኙ ልክ አይደለም", callback_data=f"rej_wrong_{t_uid}"))
        bot.edit_message_text("❓ ውድቅ የተደረገበት ምክንያት ምንድነው?", ADMIN_ID, c.message.message_id, reply_markup=kb)

    elif c.data.startswith("rej_"):
        rtype, t_uid = c.data.split("_")[1], c.data.split("_")[2]
        txt = "❌ ደረሰኝዎ ውድቅ ተደርጓል!\nምክንያት፦ ብር አነስተኛ ነው።" if rtype=="low" else "❌ ደረሰኝዎ ውድቅ ተደርጓል!\nምክንያት፦ ደረሰኙ ትክክል አይደለም።"
        bot.send_message(t_uid, txt); bot.delete_message(ADMIN_ID, c.message.message_id)

    # ቁጥር መያዝ
    elif c.data.startswith("n_"):
        bid = data["users"][uid].get("sel_bid")
        n = c.data.split("_")[1]
        if bid and data["users"][uid]["tks"] > 0:
            data["boards"][bid]["slots"][n] = {"name": data["users"][uid]["name"], "id": uid}
            data["users"][uid]["tks"] -= 1
            refresh_group(bid); bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል!")
            bot.delete_message(uid, c.message.message_id)

    # አድሚን ፓነል ስራዎች
    elif c.data == "adm_reset_main":
        kb = telebot.types.InlineKeyboardMarkup()
        for k in data["boards"]: kb.add(telebot.types.InlineKeyboardButton(f"ሰሌዳ {k} አጽዳ", callback_data=f"areset_{k}"))
        bot.edit_message_text("የትኛውን ሰሌዳ ማጽዳት ይፈልጋሉ?", ADMIN_ID, c.message.message_id, reply_markup=kb)

    elif c.data.startswith("areset_"):
        bid = c.data.split("_")[1]; data["boards"][bid]["slots"] = {}; refresh_group(bid, new=True)
        bot.answer_callback_query(c.id, "ሰሌዳው ጸድቷል!")

    elif c.data == "adm_toggle_main":
        kb = telebot.types.InlineKeyboardMarkup()
        for k, v in data["boards"].items(): kb.add(telebot.types.InlineKeyboardButton(f"{'🟢' if v['active'] else '🔴'} ሰሌዳ {k}", callback_data=f"tog_{k}"))
        bot.edit_message_text("ሰሌዳ ለመክፈት/ለመዝጋት ይጫኑ፦", ADMIN_ID, c.message.message_id, reply_markup=kb)

    elif c.data.startswith("tog_"):
        bid = c.data.split("_")[1]; data["boards"][bid]["active"] = not data["boards"][bid]["active"]; refresh_group(bid, new=True)
        bot.answer_callback_query(c.id, "ሁኔታው ተቀይሯል!")

@bot.message_handler(content_types=['text', 'photo'])
def handle_msgs(m):
    uid = str(m.from_user.id)
    u = data["users"].get(uid)
    if not u: return

    # --- የእኔ እጣ ስራ ---
    if m.text == "🎫 የእኔ እጣ":
        tickets_msg = f"🎫 **የእርስዎ የዕጣ መረጃ**\n━━━━━━━━━━━━━\n👤 ስም፦ {u['name']}\n💰 ቀሪ እጣዎች፦ `{u['tks']}`\n\n"
        found = False
        for bid, b in data["boards"].items():
            user_nums = [n for n, info in b["slots"].items() if info["id"] == uid]
            if user_nums:
                found = True
                tickets_msg += f"📍 **{b['name']}**፦ `{', '.join(user_nums)}` ቁጥሮች\n"
        if not found: tickets_msg += "⚠️ እስካሁን ምንም ቁጥር አልያዙም።"
        bot.send_message(uid, tickets_msg, parse_mode="Markdown")

    elif m.text == "🕹 ቁጥር ምረጥ":
        bid = u.get("sel_bid")
        if u['tks'] > 0 and bid:
            b = data["boards"][bid]
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            kb.add(*[telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]])
            bot.send_message(uid, f"🔢 {b['name']} ቁጥር ይምረጡ፦", reply_markup=kb)
        else: bot.send_message(uid, "❌ መጀመሪያ ሰሌዳ መርጠው ደረሰኝ ይላኩ።")

    elif u['step'] == "ASK_NAME":
        u['name'] = m.text; u['step'] = ""; save_db()
        bot.send_message(uid, "✅ ተመዝግቧል! አሁን '🕹 ቁጥር ምረጥ' የሚለውን ይጫኑ።")

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        kb.add(telebot.types.InlineKeyboardButton("♻️ ሰሌዳ አጽዳ (Reset)", callback_data="adm_reset_main"),
               telebot.types.InlineKeyboardButton("🟢/🔴 ሰሌዳ ክፈት/ዝጋ", callback_data="adm_toggle_main"))
        bot.send_message(uid, "🛠 **የአድሚን መቆጣጠሪያ ክፍል**", reply_markup=kb)

    elif m.content_type == 'photo' or (m.text and re.search(r"(FT|DCA|[0-9]{10})", m.text)):
        bid = u.get("sel_bid")
        if not bid: bot.send_message(uid, "⚠️ መጀመሪያ ሰሌዳ ይምረጡ (/start)"); return
        price = data["boards"][bid]["price"]
        
        # SMS ብር ቼክ ማድረግ
        if m.text:
            amt_match = re.search(r"(\d+)", m.text)
            if amt_match and float(amt_match.group(1)) < price:
                bot.send_message(uid, f"❌ የላኩት ብር ከሰሌዳው ዋጋ ({price} ETB) በታች ስለሆነ ደረሰኙ ውድቅ ተደርጓል።"); return

        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_{price}_{bid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
        
        if m.content_type == 'photo': bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 ፎቶ ከ {m.from_user.first_name}\nሰሌዳ {bid}", reply_markup=kb)
        else: bot.send_message(ADMIN_ID, f"📩 SMS ከ {m.from_user.first_name}\nሰሌዳ {bid}\n`{m.text}`", reply_markup=kb, parse_mode="Markdown")
        bot.send_message(uid, "📩 ደረሰኝ ተልኳል፣ እስኪረጋገጥ ይጠብቁ።")

# --- SERVER ---
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
