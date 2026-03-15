import telebot, re, os, json, time
from flask import Flask
from threading import Thread, Lock

# --- 1. SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  

# Threaded=True ለፍጥነት እና ለብዙ ተጠቃሚዎች
bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=40)
app = Flask(__name__)
data_lock = Lock() # ለደህንነት ሲባል (Race condition መከላከያ)

# --- 2. DATA STRUCTURE ---
data = {
    "config": {"db_msg_id": None},
    "boards": {
        "1": {"name": "ሰሌዳ 1 (1-100)", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 20},
        "2": {"name": "ሰሌዳ 2 (1-50)", "max": 50, "active": True, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 10},
        "3": {"name": "ሰሌዳ 3 (1-25)", "max": 25, "active": True, "slots": {}, "msg_id": None, "prizes": [100, 50, 20], "price": 5}
    },
    "users": {}
}

# --- 3. DATABASE ENGINE ---
def save_db():
    with data_lock:
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

# --- 4. UI & GROUP ENGINE ---
def refresh_group(bid, new=False):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    txt = f"🔥 **{b['name']}** {status}\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{b['price']} ETB` | 🎁 **ሽልማት:** `{sum(b['prizes'])} ETB` \n━━━━━━━━━━━━━\n"
    
    # ሰሌዳውን በ 3 ረድፍ የማሳየት ጥበብ
    for i in range(1, b["max"] + 1):
        n = str(i)
        if n in b["slots"]:
            # የተያዙ ቁጥሮች በስም የመጀመሪያ 4 ፊደል
            name = b["slots"][n]["name"][:4]
            txt += f"{i:02d}.{name}🏆 "
        else:
            txt += f"{i:02d}.⚪️ "
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
        data["users"][uid] = {"tks": 0, "wallet": 0, "name": None, "step": "", "sel_bid": None}
    
    kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]:
            kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} - ({v['price']} ETB)", callback_data=f"sel_bd_{k}"))
    
    main_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    main_kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ መረጃ")
    if int(uid) == ADMIN_ID: main_kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, f"👋 ሰላም {m.from_user.first_name}!\nእንኳን ወደ ፋሲል ልዩ ዕጣ በሰላም መጡ።\n\nለመጫወት መጀመሪያ ሰሌዳ ይምረጡ፦", reply_markup=main_kb)
    bot.send_message(uid, "👇 ሰሌዳ እዚህ ይምረጡ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    u = data["users"].get(uid)
    if not u: return

    # ሰሌዳ መምረጥ
    if c.data.startswith("sel_bd_"):
        bid = c.data.split("_")[-1]
        u["sel_bid"] = bid
        b = data["boards"][bid]
        bot.edit_message_text(f"✅ **{b['name']} ተመርጧል!**\n💰 መደብ፦ `{b['price']} ETB` \n🏦 CBE: `1000584461757` \n📱 Telebirr: `0951381356` \n━━━━━━━━━━━━━\n📩 እባክዎ ደረሰኝ ወይም SMS እዚህ ይላኩ።", uid, c.message.message_id, parse_mode="Markdown")

    # ቁጥር መምረጥ (ዋናው ሎጂክ)
    elif c.data.startswith("pick_"):
        bid = u.get("sel_bid")
        n = c.data.split("_")[1]
        
        with data_lock: # በተመሳሳይ ሰከንድ ሁለት ሰው እንዳይነካ መቆለፍ
            if bid and u["tks"] > 0:
                if n not in data["boards"][bid]["slots"]:
                    data["boards"][bid]["slots"][n] = {"name": u["name"], "id": uid}
                    u["tks"] -= 1
                    
                    # 1. ግሩፕ ላይ ማሳወቅ
                    bot.send_message(GROUP_ID, f"🎉 **{u['name']}** ከሰሌዳ {bid} ቁጥር **{n}**ን መርጧል!\n💰 ቀሪ እጣ፦ `{u['tks']}`")
                    
                    # 2. ሰሌዳውን አፕዴት ማድረግ
                    refresh_group(bid)
                    
                    # 3. ለተጠቃሚው ቀጣይ ምርጫ መስጠት
                    if u["tks"] > 0:
                        kb = telebot.types.InlineKeyboardMarkup(row_width=5)
                        b = data["boards"][bid]
                        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"pick_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
                        kb.add(*btns)
                        bot.edit_message_text(f"✅ ቁጥር {n} ተይዟል! ቀሪ {u['tks']} እጣ አለዎት። ሌላ ይምረጡ፦", uid, c.message.message_id, reply_markup=kb)
                    else:
                        bot.edit_message_text(f"✅ ቁጥር {n} ተይዟል! ሁሉንም እጣዎን ጨርሰዋል። መልካም እድል!", uid, c.message.message_id)
                else:
                    bot.answer_callback_query(c.id, "⚠️ ይቅርታ፣ ይህ ቁጥር አሁን ተይዟል!", show_alert=True)
            else:
                bot.answer_callback_query(c.id, "❌ እጣ የለዎትም!", show_alert=True)

    # አድሚን ማጽደቅ
    elif c.data.startswith("adm_ok_") and int(uid) == ADMIN_ID:
        _, _, t_uid, bid = c.data.split("_")
        u_target = data["users"].get(t_uid)
        u_target["step"] = f"WAIT_AMT_{t_uid}_{bid}"
        bot.send_message(ADMIN_ID, f"💰 ለ {u_target.get('name', t_uid)} ስንት ብር ተላከ? (ቁጥር ብቻ)፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)

    elif c.data.startswith("adm_rej_") and int(uid) == ADMIN_ID:
        t_uid = c.data.split("_")[-1]
        bot.send_message(t_uid, "❌ ደረሰኝዎ ውድቅ ተደርጓል። እባክዎ ትክክለኛ ደረሰኝ ይላኩ ወይም አድሚኑን ያነጋግሩ።")
        bot.delete_message(ADMIN_ID, c.message.message_id)

@bot.message_handler(content_types=['text', 'photo'])
def handle_msgs(m):
    uid = str(m.from_user.id)
    u = data["users"].get(uid)
    if not u: return

    # አድሚን ብር ሲያስገባ
    if u["step"].startswith("WAIT_AMT_") and int(uid) == ADMIN_ID:
        try:
            _, _, t_uid, bid = u["step"].split("_")
            amt = float(m.text)
            price = data["boards"][bid]["price"]
            
            new_tks = int(amt // price)
            rem = amt % price
            
            data["users"][t_uid]["tks"] += new_tks
            data["users"][t_uid]["wallet"] += rem
            u["step"] = ""
            
            # ግሩፕ ላይ ማሳወቅ
            bot.send_message(GROUP_ID, f"✅ የ **{data['users'][t_uid].get('name', 'ተጠቃሚ')}** ክፍያ ጸድቋል!\n🎫 `{new_tks}` እጣ ተሰጥቷል።")
            
            if not data["users"][t_uid]["name"]:
                data["users"][t_uid]["step"] = "ASK_NAME"
                bot.send_message(t_uid, "✅ ክፍያዎ ጸድቋል! እባክዎ ስምዎን ይጻፉ፦")
            else:
                bot.send_message(t_uid, f"✅ {new_tks} እጣ ተጨምሯል! ቁጥር ለመምረጥ '🕹 ቁጥር ምረጥ' የሚለውን ይጫኑ።")
            
            save_db(); bot.send_message(ADMIN_ID, "✅ ተፈጽሟል።")
        except: bot.send_message(ADMIN_ID, "❌ ስህተት! ቁጥር ብቻ ያስገቡ።")
        return

    # ስም መቀበያ
    if u["step"] == "ASK_NAME":
        u["name"] = m.text
        u["step"] = ""
        save_db()
        bot.send_message(uid, f"✅ ተመዝግቧል {m.text}! አሁን ቁጥር መምረጥ ይችላሉ።", reply_markup=telebot.types.ReplyKeyboardRemove())
        # ቁጥር መምረጫውን ወዲያው አምጣለት
        bid = u.get("sel_bid")
        if bid:
            b = data["boards"][bid]
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"pick_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
            kb.add(*btns)
            bot.send_message(uid, f"🔢 {b['name']} ቁጥር ይምረጡ፦", reply_markup=kb)
        return

    # ቁጥር መምረጫ በተን
    if m.text == "🕹 ቁጥር ምረጥ":
        bid = u.get("sel_bid")
        if u["tks"] > 0 and bid:
            b = data["boards"][bid]
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"pick_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
            kb.add(*btns)
            bot.send_message(uid, f"🔢 {b['name']} ቁጥር ይምረጡ (ቀሪ እጣ፦ {u['tks']})፦", reply_markup=kb)
        else:
            bot.send_message(uid, "❌ መጀመሪያ ሰሌዳ መርጠው ደረሰኝ ይላኩ (ወይም እጣዎ አልቋል)።")

    # የእኔ መረጃ
    if m.text == "🎫 የእኔ መረጃ":
        msg = f"🎫 **የእርስዎ መረጃ**\n━━━━━━━━━━━━━\n👤 ስም፦ {u['name']}\n💰 ቀሪ እጣ፦ `{u['tks']}`\n💵 ዋሌት፦ `{u['wallet']} ETB` \n━━━━━━━━━━━━━\n"
        bot.send_message(uid, msg)

    # አድሚን ፓነል
    if m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        kb.add(telebot.types.InlineKeyboardButton("♻️ ሰሌዳ 1 አጽዳ (Reset)", callback_data="adm_reset_1"),
               telebot.types.InlineKeyboardButton("⚙️ ሰሌዳ 1 ክፈት/ዝጋ", callback_data="adm_tog_1"))
        bot.send_message(uid, "🛠 **Admin Control Panel**", reply_markup=kb)

    # ደረሰኝ መቀበያ
    if m.content_type == 'photo' or (m.text and len(m.text) > 10):
        if m.chat.id == GROUP_ID: return
        bid = u.get("sel_bid")
        if not bid: 
            bot.send_message(uid, "⚠️ መጀመሪያ ሰሌዳ ይምረጡ!")
            return
        
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"adm_ok_{uid}_{bid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"adm_rej_{uid}"))
        
        bot.send_message(ADMIN_ID, f"📩 አዲስ ደረሰኝ ከ {m.from_user.first_name} (ሰሌዳ {bid})", reply_markup=kb)
        if m.content_type == 'photo': bot.forward_message(ADMIN_ID, m.chat.id, m.message_id)
        else: bot.send_message(ADMIN_ID, f"SMS: {m.text}")
        bot.send_message(uid, "📩 ደረሰኝዎ ተልኳል። አድሚኑ እስኪያጸድቅ በትዕግስት ይጠብቁ።")

# --- 6. SERVER & RUN ---
@app.route('/')
def home(): return "Bot is Running!"

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    print("Bot is Polling...")
    bot.infinity_polling()
