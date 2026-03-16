import telebot, json, re
from telebot import types

# --- 1. SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  

bot = telebot.TeleBot(TOKEN, threaded=False)

# --- 2. DATA STRUCTURE ---
data = {
    "config": {"db_msg_id": None},
    "boards": {
        "1": {"name": "ሰሌዳ 1-100", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 100},
        "2": {"name": "ሰሌዳ 1-50", "max": 50, "active": True, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 50},
        "3": {"name": "ሰሌዳ 1-25", "max": 25, "active": True, "slots": {}, "msg_id": None, "prizes": [100, 50, 25], "price": 25}
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
        msgs = bot.get_chat_history(DB_CHANNEL_ID, limit=10)
        for m in msgs:
            if m.text and "💾 DB_STORAGE" in m.text:
                loaded = json.loads(m.text.replace("💾 DB_STORAGE", "").strip())
                data.update(loaded)
                return True
    except: pass
    return False

# --- 4. UI ENGINE ---
def refresh_group(bid, new=False):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    total_prize = sum(b["prizes"])
    txt = f"🔥 **{b['name']}** {status}\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{b['price']} ETB` | 🎁 **ሽልማት:** `{total_prize} ETB` \n━━━━━━━━━━━━━\n"
    
    for i in range(1, b["max"] + 1):
        n = str(i)
        txt += f"{i:02d}.{b['slots'][n]['name'][:4]}✅ " if n in b["slots"] else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    
    txt += f"\n🥇 {b['prizes'][0]} | 🥈 {b['prizes'][1]} | 🥉 {b['prizes'][2]}"
    txt += f"\n━━━━━━━━━━━━━\n🕹 @{bot.get_me().username}"
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
        data["users"][uid] = {"wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    
    main_kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    main_kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ ዋሌት")
    if int(uid) == ADMIN_ID: main_kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, f"ሰላም {m.from_user.first_name}! እንኳን መጡ።", reply_markup=main_kb)
    kb = types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]: kb.add(types.InlineKeyboardButton(f"🎰 {v['name']} ({v['price']} ETB)", callback_data=f"sel_{k}"))
    bot.send_message(uid, "👇 መሳተፍ የሚፈልጉትን ሰሌዳ ይምረጡ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    
    if c.data.startswith("sel_"):
        bid = c.data.split("_")[1]
        data["users"][uid]["sel_bid"] = bid
        bot.edit_message_text(f"✅ ሰሌዳ {bid} ተመርጧል!\n\n📩 ደረሰኝ ወይም SMS እዚህ ይላኩ።", uid, c.message.message_id)

    elif c.data.startswith("approve_") and int(uid) == ADMIN_ID:
        _, t_uid, bid = c.data.split("_")
        data["users"][uid]["step"] = f"AMT_{t_uid}_{bid}"
        bot.send_message(ADMIN_ID, "✍️ የተቀበልከውን የብር መጠን በቁጥር ብቻ ጻፍ (ምሳሌ፡ 550)፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)

    elif c.data.startswith("decline_") and int(uid) == ADMIN_ID:
        t_uid = c.data.split("_")[1]
        data["users"][uid]["step"] = f"REJ_{t_uid}"
        bot.send_message(ADMIN_ID, "✍️ ውድቅ የተደረገበትን ምክንያት ጻፍ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)

    elif c.data.startswith("num_"):
        bid = data["users"][uid].get("sel_bid")
        n = c.data.split("_")[1]
        if not bid: return
        price = data["boards"][bid]["price"]
        
        if data["users"][uid]["wallet"] >= price:
            if n not in data["boards"][bid]["slots"]:
                data["boards"][bid]["slots"][n] = {"name": data["users"][uid]["name"], "id": uid}
                data["users"][uid]["wallet"] -= price
                refresh_group(bid)
                bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተመዝግቧል!")
                bot.send_message(uid, f"✅ ቁጥር {n} ተመዝግቧል!\n💰 ቀሪ ዋሌት፦ {data['users'][uid]['wallet']} ETB")
                bot.delete_message(uid, c.message.message_id)
            else: bot.answer_callback_query(c.id, "⚠️ ቁጥሩ ተይዟል!", show_alert=True)
        else: bot.answer_callback_query(c.id, "❌ በቂ ብር የለዎትም!", show_alert=True)

    elif c.data == "adm_reset" and int(uid) == ADMIN_ID:
        for k in data["boards"]: 
            data["boards"][k]["slots"] = {}
            refresh_group(k, new=True)
        bot.answer_callback_query(c.id, "ሁሉም ሰሌዳዎች ጸድተዋል!")

    elif c.data == "adm_toggle" and int(uid) == ADMIN_ID:
        kb = types.InlineKeyboardMarkup()
        for k, v in data["boards"].items(): kb.add(types.InlineKeyboardButton(f"{v['name']} {'🟢' if v['active'] else '🔴'}", callback_data=f"tog_{k}"))
        bot.send_message(ADMIN_ID, "ሰሌዳ ኦን/ኦፍ ለማድረግ ይጫኑ፦", reply_markup=kb)

    elif c.data.startswith("tog_") and int(uid) == ADMIN_ID:
        bid = c.data.split("_")[1]
        data["boards"][bid]["active"] = not data["boards"][bid]["active"]; refresh_group(bid, new=True)

@bot.message_handler(content_types=['text', 'photo'])
def handle_msgs(m):
    uid = str(m.from_user.id)
    u = data["users"].get(uid)
    if not u: return

    # --- ሎጂክ ማስተካከያ (Step Checking) ---
    
    # አድሚን ብር ሲመዘግብ
    if u.get('step', '').startswith("AMT_") and int(uid) == ADMIN_ID:
        _, t_uid, bid = u['step'].split("_")
        try:
            amt = float(m.text)
            data["users"][t_uid]["wallet"] += amt
            data["users"][t_uid]["step"] = "ASK_NAME"
            bot.send_message(t_uid, f"✅ ደረሰኝዎ ጸድቋል! {amt} ብር ዋሌትዎ ላይ ተጨምሯል።\n\nአሁን ስምዎን ይጻፉ፦")
            bot.send_message(ADMIN_ID, "✅ ብሩ ተመዝግቧል!")
            u['step'] = ""; save_db()
        except: bot.send_message(ADMIN_ID, "⚠️ እባክህ ቁጥር ብቻ ጻፍ")
        return

    # ውድቅ ሲደረግ ምክንያት
    elif u.get('step', '').startswith("REJ_") and int(uid) == ADMIN_ID:
        t_uid = u['step'].split("_")[1]
        bot.send_message(t_uid, f"❌ ደረሰኝዎ ውድቅ ተደርጓል!\nምክንያት፦ {m.text}")
        bot.send_message(ADMIN_ID, "✅ ለተጠቃሚው ተልኳል")
        u['step'] = ""; save_db()
        return

    # ተጠቃሚ ስም ሲመዘግብ (ይህ ክፍል ነው ስህተት የነበረው)
    elif u.get('step') == "ASK_NAME":
        u['name'] = m.text
        u['step'] = ""
        save_db()
        bot.send_message(uid, f"✅ ስምዎ '{m.text}' ተብሎ ተመዝግቧል! አሁን '🕹 ቁጥር ምረጥ'ን በመጫን ይሳተፉ።")
        return

    # አድሚን ዋጋና ሽልማት መቀየሪያ (Text based)
    elif int(uid) == ADMIN_ID and m.text and (m.text.upper().startswith('P') or m.text.upper().startswith('W')):
        try:
            cmd = m.text[0].upper()
            bid = m.text[1]
            if cmd == 'P':
                p_list = [int(x.strip()) for x in m.text[2:].strip().split(',')]
                if len(p_list) == 3:
                    data["boards"][bid]["prizes"] = p_list
                    bot.send_message(ADMIN_ID, f"✅ ሰሌዳ {bid} ሽልማት {p_list} ሆኗል።")
                    refresh_group(bid)
                else: bot.send_message(ADMIN_ID, "⚠️ 3 ሽልማቶችን በኮማ ይለዩ (ምሳሌ፡ P1 500,300,100)")
            elif cmd == 'W':
                val = int(m.text[2:].strip())
                data["boards"][bid]["price"] = val
                bot.send_message(ADMIN_ID, f"✅ ሰሌዳ {bid} ዋጋ {val} ሆኗል።")
                refresh_group(bid)
            save_db()
        except: bot.send_message(ADMIN_ID, "⚠️ ስህተት! አጻጻፍ፡ P1 500,300,100 ወይም W1 100")
        return

    # --- MAIN MENU BUTTONS ---
    if m.text == "🕹 ቁጥር ምረጥ":
        bid = u.get("sel_bid")
        if not bid: 
            bot.send_message(uid, "❌ መጀመሪያ ሰሌዳ ይምረጡ")
            return
        b = data["boards"][bid]
        if u["wallet"] < b["price"]: 
            bot.send_message(uid, f"❌ በቂ ብር የለዎትም! (ያለዎት፦ {u['wallet']} ETB)")
        else:
            kb = types.InlineKeyboardMarkup(row_width=5)
            btns = [types.InlineKeyboardButton(str(i), callback_data=f"num_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
            kb.add(*btns)
            bot.send_message(uid, f"🔢 {b['name']} ቁጥር ይምረጡ (ዋሌት፦ {u['wallet']} ETB)፦", reply_markup=kb)

    elif m.text == "🎫 የእኔ ዋሌት":
        bot.send_message(uid, f"👤 ስም፦ {u['name']}\n💰 ቀሪ ዋሌት፦ {u['wallet']} ETB")

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("♻️ Reset & Send Board", callback_data="adm_reset"),
               types.InlineKeyboardButton("🏆 ሽልማት (P1 500,300,100)", callback_data="help_p"),
               types.InlineKeyboardButton("💰 ዋጋ (W1 100)", callback_data="help_w"),
               types.InlineKeyboardButton("⚙️ ሰሌዳ On/Off", callback_data="adm_toggle"))
        bot.send_message(uid, "🛠 **አድሚን ፓነል**\n\nዋጋ ለመቀየር፡ `W1 100` ብለው ይላኩ\nሽልማት ለመቀየር፡ `P1 500,300,100` ብለው ይላኩ", reply_markup=kb)

    # ደረሰኝ መቀበያ
    elif m.content_type == 'photo' or (m.text and len(m.text) > 10):
        bid = u.get("sel_bid")
        if not bid: 
            bot.send_message(uid, "⚠️ መጀመሪያ ሰሌዳ ይምረጡ")
            return
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"approve_{uid}_{bid}"),
               types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"decline_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 ደረሰኝ ከ {m.from_user.first_name}\nሰሌዳ፡ {bid}", reply_markup=kb)
        if m.content_type == 'photo': bot.send_photo(ADMIN_ID, m.photo[-1].file_id)
        else: bot.send_message(ADMIN_ID, f"SMS: {m.text}")
        bot.send_message(uid, "📩 ደረሰኝ ደርሶናል! አድሚኑ እስኪያረጋግጥ ይጠብቁ።")

if __name__ == "__main__":
    load_db()
    bot.infinity_polling()
