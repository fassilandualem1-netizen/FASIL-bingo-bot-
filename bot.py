import telebot, re, json, time
from flask import Flask
from threading import Thread

# --- 1. SETUP ---
# ማሳሰቢያ፡ Token-ህን ለጥንቃቄ መቀየር (Revoke) አትርሳ
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
        "3": {"name": "ሰሌዳ 3 (1-25)", "max": 25, "active": False, "slots": {}, "msg_id": None, "prizes": [100, 50, 20], "price": 5}
    },
    "users": {}
}

# --- 3. DATABASE ENGINE ---
def save_db():
    try:
        payload = "💾 DB_STORAGE " + json.dumps(data)
        db_id = data["config"].get("db_msg_id")
        if db_id: 
            bot.edit_message_text(payload, DB_CHANNEL_ID, db_id)
        else:
            m = bot.send_message(DB_CHANNEL_ID, payload)
            data["config"]["db_msg_id"] = m.message_id
            bot.pin_chat_message(DB_CHANNEL_ID, m.message_id)
    except Exception as e: 
        print(f"Save Error: {e}")

def load_db():
    try:
        chat = bot.get_chat(DB_CHANNEL_ID)
        if chat.pinned_message and "💾 DB_STORAGE" in chat.pinned_message.text:
            raw = chat.pinned_message.text.replace("💾 DB_STORAGE", "").strip()
            loaded = json.loads(raw)
            data.update(loaded)
            return True
    except Exception as e: 
        print(f"Load Error: {e}")
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
        else: 
            bot.edit_message_text(txt, GROUP_ID, b["msg_id"], parse_mode="Markdown")
    except: pass
    save_db()

# --- 5. HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: 
        data["users"][uid] = {"wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None, "tks": 0}
    
    main_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    main_kb.add("🕹 ቁጥር ምረጥ", "💰 ዋሌትና መረጃ", "🎫 የእኔ እጣ")
    if int(uid) == ADMIN_ID: main_kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, f"🌟 **እንኳን ወደ ፋሲል ልዩ ዕጣ በሰላም መጡ!** 🌟\n\nለመጫወት መጀመሪያ ሰሌዳ ይምረጡ፦", reply_markup=main_kb, parse_mode="Markdown")
    
    kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]:
            kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} - ({v['price']} ETB)", callback_data=f"start_sel_{k}"))
    bot.send_message(uid, "👇 ሰሌዳ እዚህ ይምረጡ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    u = data["users"].get(uid)
    if not u: return

    if c.data.startswith("start_sel_"):
        bid = c.data.split("_")[-1]
        u["sel_bid"] = bid
        b = data["boards"][bid]
        bot.edit_message_text(f"✅ **{b['name']} ተመርጧል!**\n💰 መደብ፦ `{b['price']} ETB` \n🏦 CBE: `1000584461757` | 📱 Telebirr: `0951381356` \n━━━━━━━━━━━━━\n📩 እባክዎ ደረሰኝ እዚህ ይላኩ።", uid, c.message.message_id, parse_mode="Markdown")

    elif c.data.startswith("ok_") and int(uid) == ADMIN_ID:
        _, t_uid, amt, bid = c.data.split("_")
        amt_val = float(amt)
        data["users"][t_uid]["wallet"] += amt_val
        data["users"][t_uid]["step"] = "ASK_NAME" if not data["users"][t_uid].get("name") else ""
        msg = f"✅ ደረሰኝዎ ጸድቋል!\n💰 `{amt_val} ETB` ዋሌትዎ ላይ ተቀምጧል።\n\nአሁን '🕹 ቁጥር ምረጥ' የሚለውን ተጭነው መጫወት ይችላሉ።"
        bot.send_message(t_uid, msg)
        bot.delete_message(ADMIN_ID, c.message.message_id); save_db()

    elif c.data.startswith("manual_") and int(uid) == ADMIN_ID:
        _, t_uid, bid = c.data.split("_")
        data["users"][uid]["step"] = f"INPUT_AMT_{t_uid}_{bid}"
        bot.send_message(ADMIN_ID, "✍️ እባክህ ለዚህ ደረሰኝ የሚመዘገበውን የብር መጠን በቁጥር ብቻ ጻፍ፦")

    elif c.data.startswith("n_"):
        bid = u.get("sel_bid")
        n = c.data.split("_")[1]
        if bid:
            b = data["boards"][bid]
            price = b["price"]
            if u["wallet"] >= price:
                if n not in b["slots"]:
                    u["wallet"] -= price
                    b["slots"][n] = {"name": u["name"], "id": uid}
                    refresh_group(bid)
                    bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል! {price} ETB ተቀንሷል።")
                    bot.delete_message(uid, c.message.message_id)
                else: bot.answer_callback_query(c.id, "⚠️ ይቅርታ፣ ይህ ቁጥር ተይዟል!", show_alert=True)
            else: bot.answer_callback_query(c.id, f"❌ በቂ ብር የለዎትም! (ያስፈልጋል: {price} ETB)", show_alert=True)
        else: bot.answer_callback_query(c.id, "❌ መጀመሪያ ሰሌዳ ይምረጡ!", show_alert=True)

    # ... [የቀሩት Admin Logic (Reset, Toggle, Price) እዚህ ይቀጥላሉ] ...
    elif c.data == "adm_reset_main" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup()
        for k in data["boards"]: kb.add(telebot.types.InlineKeyboardButton(f"ሰሌዳ {k} አጽዳ", callback_data=f"areset_{k}"))
        bot.send_message(ADMIN_ID, "የትኛውን ሰሌዳ ማጽዳት ይፈልጋሉ?", reply_markup=kb)
    
    elif c.data.startswith("areset_") and int(uid) == ADMIN_ID:
        bid = c.data.split("_")[1]; data["boards"][bid]["slots"] = {}; refresh_group(bid, new=True); bot.answer_callback_query(c.id, "ጸድቷል!")

@bot.message_handler(content_types=['text', 'photo'])
def handle_msgs(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: 
        data["users"][uid] = {"wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None, "tks": 0}
    u = data["users"][uid]

    if u['step'].startswith("INPUT_AMT_") and int(uid) == ADMIN_ID:
        _, _, t_uid, bid = u['step'].split("_")
        try:
            amt_val = float(m.text)
            data["users"][t_uid]["wallet"] += amt_val
            data["users"][t_uid]["step"] = "ASK_NAME" if not data["users"][t_uid].get("name") else ""
            u['step'] = ""
            bot.send_message(t_uid, f"✅ ደረሰኝዎ ጸድቋል!\n💰 `{amt_val} ETB` ዋሌትዎ ላይ ተቀምጧል።")
            bot.send_message(ADMIN_ID, "✅ ተመዝግቧል!"); save_db()
        except: bot.send_message(ADMIN_ID, "⚠️ ቁጥር ብቻ ይጻፉ።")
        return

    if m.text == "💰 ዋሌትና መረጃ":
        msg = f"👤 **ስም፦** {u['name']}\n💰 **ቀሪ ዋሌት፦** `{u['wallet']} ETB` \n📍 **የተመረጠ ሰሌዳ፦** {data['boards'].get(u['sel_bid'], {'name': 'አልተመረጠም'})['name']}"
        bot.send_message(uid, msg, parse_mode="Markdown")

    elif m.text == "🕹 ቁጥር ምረጥ":
        bid = u.get("sel_bid")
        if not bid:
            bot.send_message(uid, "⚠️ መጀመሪያ ሰሌዳ ይምረጡ።")
            return
        b = data["boards"][bid]
        if u["wallet"] < b["price"]:
            bot.send_message(uid, f"❌ ዋሌትዎ ላይ በቂ ብር የለም። የሰሌዳው ዋጋ {b['price']} ETB ነው።")
            return
        kb = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
        kb.add(*btns)
        bot.send_message(uid, f"🔢 {b['name']} ቁጥር ይምረጡ (ዋጋ፦ {b['price']} ETB)፦", reply_markup=kb)

    elif u['step'] == "ASK_NAME":
        u['name'] = m.text; u['step'] = ""; save_db()
        bot.send_message(uid, "✅ ስምዎ ተመዝግቧል! አሁን መጫወት ይችላሉ።")

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        kb.add(telebot.types.InlineKeyboardButton("♻️ ሰሌዳ አጽዳ (Reset)", callback_data="adm_reset_main"))
        bot.send_message(uid, "🛠 **የአድሚን መቆጣጠሪያ ክፍል**", reply_markup=kb)

    elif m.content_type == 'photo' or (m.text and re.search(r"(FT|DCA|[0-9]{10})", m.text)):
        bid = u.get("sel_bid")
        if not bid: 
            bot.send_message(uid, "⚠️ መጀመሪያ ሰሌዳ ይምረጡ።")
            return
        
        kb = telebot.types.InlineKeyboardMarkup()
        # ለቀላል አሰራር default 20 ETB ተደርጓል፤ አድሚኑ ግን መቀየር ይችላል
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ (20 ETB)", callback_data=f"ok_{uid}_20_{bid}"),
               telebot.types.InlineKeyboardButton("✅ በቁጥር አጽድቅ", callback_data=f"manual_{uid}_{bid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
        
        if m.content_type == 'photo': 
            bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 ደረሰኝ ከ {m.from_user.first_name}\nሰሌዳ {bid}", reply_markup=kb)
        else: 
            bot.send_message(ADMIN_ID, f"📩 SMS ከ {m.from_user.first_name}\nሰሌዳ {bid}\n`{m.text}`", reply_markup=kb)
        bot.send_message(uid, "📩 ደረሰኝዎ ለቁጥጥር ተልኳል! እባክዎን በትዕግስት ይጠብቁ።")

# --- 6. SERVER & POLLING ---
@app.route('/')
def home(): return "Bot is Running!"

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    print("Bot is starting...")
    bot.infinity_polling()
