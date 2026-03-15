import telebot, json, time

# --- 1. SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  

bot = telebot.TeleBot(TOKEN, threaded=True)

# --- 2. DATA STRUCTURE ---
data = {
    "config": {"db_msg_id": None},
    "boards": {
        "1": {"name": "ሰሌዳ 1 (1-100)", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 20},
        "2": {"name": "ሰሌዳ 2 (1-50)", "max": 50, "active": False, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 10},
        "3": {"name": "ሰሌዳ 3 (1-25)", "max": 25, "active": False, "slots": {}, "msg_id": None, "prizes": [100, 50, 20], "price": 5}
    },
    "users": {} # "uid": {"balance": 0, "name": "...", "step": "", "sel_bid": None}
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
                data["users"].update(loaded.get("users", {}))
                data["boards"].update(loaded.get("boards", {}))
                data["config"].update(loaded.get("config", {}))
                return True
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
        data["users"][uid] = {"balance": 0, "name": m.from_user.first_name, "step": "", "sel_bid": "1"}
    
    kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]:
            kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} - ({v['price']} ETB)", callback_data=f"start_sel_{k}"))
    
    main_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    main_kb.add("🕹 ቁጥር ምረጥ", "💰 የእኔ ሂሳብ (Wallet)")
    if int(uid) == ADMIN_ID: main_kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, f"🌟 **እንኳን ወደ ፋሲል ልዩ ዕጣ በሰላም መጡ!** 🌟\n\nየእርስዎ ቀሪ ሂሳብ፦ `{data['users'][uid]['balance']} ETB`", reply_markup=main_kb, parse_mode="Markdown")
    bot.send_message(uid, "👇 ለመጫወት ሰሌዳ ይምረጡ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    
    if c.data.startswith("start_sel_"):
        bid = c.data.split("_")[-1]
        data["users"][uid]["sel_bid"] = bid
        b = data["boards"][bid]
        bot.edit_message_text(f"✅ **{b['name']} ተመርጧል!**\n💰 የአንድ እጣ ዋጋ፦ `{b['price']} ETB` \n🏦 CBE: `1000584461757` | 📱 Telebirr: `0951381356` \n━━━━━━━━━━━━━\n📩 ብር ከከፈሉ በኋላ ደረሰኝ እዚህ ይላኩ።", uid, c.message.message_id, parse_mode="Markdown")

    elif c.data.startswith("ok_") and int(uid) == ADMIN_ID:
        target_uid = c.data.split("_")[1]
        data["users"][uid]["step"] = f"ADD_MONEY_{target_uid}"
        bot.send_message(ADMIN_ID, f"💰 ለተጠቃሚ {target_uid} የሚጨመረውን የብር መጠን ያስገቡ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)

    elif c.data.startswith("n_"):
        u = data["users"][uid]
        bid = u.get("sel_bid", "1")
        b = data["boards"][bid]
        num = c.data.split("_")[1]
        
        if u["balance"] >= b["price"]:
            if num not in b["slots"]:
                u["balance"] -= b["price"]
                b["slots"][num] = {"name": u["name"], "id": uid}
                bot.answer_callback_query(c.id, f"✅ ቁጥር {num} ተይዟል! ቀሪ ሂሳብ፦ {u['balance']} ETB")
                refresh_group(bid)
                save_db()
            else: bot.answer_callback_query(c.id, "⚠️ ይሄ ቁጥር ተይዟል!", show_alert=True)
        else: bot.answer_callback_query(c.id, f"❌ በቂ ሂሳብ የለዎትም! የአንድ እጣ ዋጋ {b['price']} ETB ነው።", show_alert=True)

@bot.message_handler(content_types=['text', 'photo'])
def handle_all(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"balance": 0, "name": m.from_user.first_name, "step": "", "sel_bid": "1"}
    u = data["users"][uid]

    if m.content_type == 'photo':
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"no_{uid}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 **አዲስ ደረሰኝ**\nከ፦ {m.from_user.first_name}\nID: `{uid}`", reply_markup=kb, parse_mode="Markdown")
        bot.reply_to(m, "✅ ደረሰኝዎ ተልኳል። አድሚኑ ሲያጸድቅልዎ ብር ዋሌትዎ ላይ ይደመራል!")

    elif m.content_type == 'text':
        if u["step"].startswith("ADD_MONEY_") and int(uid) == ADMIN_ID:
            target_uid = u["step"].split("_")[-1]
            try:
                amount = int(m.text)
                if target_uid not in data["users"]: data["users"][target_uid] = {"balance": 0, "name": "User", "step": ""}
                
                # ሂሳብ መደመር logic
                old_bal = data["users"][target_uid]["balance"]
                data["users"][target_uid]["balance"] += amount
                u["step"] = ""
                
                bot.send_message(target_uid, f"✅ ደረሰኝዎ ጸድቋል!\n💰 የተደመረ፦ {amount} ETB\n💵 ጠቅላላ ቀሪ ሂሳብ፦ {data['users'][target_uid]['balance']} ETB")
                bot.send_message(ADMIN_ID, f"✅ ለተጠቃሚ {target_uid} {amount} ETB ተጨምሯል። (ነባር {old_bal} + {amount} = {data['users'][target_uid]['balance']})")
                save_db()
            except: bot.send_message(ADMIN_ID, "❌ እባክዎ ቁጥር ብቻ ያስገቡ!")

        elif m.text == "🕹 ቁጥር ምረጥ":
            bid = u.get("sel_bid", "1")
            b = data["boards"][bid]
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(f"{'✅' if str(i) in b['slots'] else i}", callback_data=f"n_{i}") for i in range(1, b["max"]+1)]
            kb.add(*btns)
            bot.send_message(uid, f"🎰 **{b['name']}**\nየሚፈልጉትን ቁጥር ይምረጡ (ዋጋ፦ {b['price']} ETB)፦", reply_markup=kb)

        elif m.text == "💰 የእኔ ሂሳብ (Wallet)":
            bot.send_message(uid, f"👤 **ስም፦** {u['name']}\n💰 **ቀሪ ሂሳብ፦** `{u['balance']} ETB`")

# --- 6. RUN ---
if __name__ == "__main__":
    load_db()
    print("Bot is online...")
    bot.infinity_polling()
