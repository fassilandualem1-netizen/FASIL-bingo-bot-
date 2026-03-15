import telebot, json, time, random
from flask import Flask
from threading import Thread, Lock

# --- 1. SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  

bot = telebot.TeleBot(TOKEN, threaded=True, num_threads=50)
app = Flask(__name__)
data_lock = Lock()

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
            if "💾 DB_STORAGE" in m.text:
                data.update(json.loads(m.text.replace("💾 DB_STORAGE", "").strip()))
                return True
    except: return False

# --- 4. UI ENGINE ---
def refresh_group_board(bid):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    txt = f"🔥 **{b['name']}** {status}\n━━━━━━━━━━━━━\n"
    txt += f"💵 **የአሁኑ መደብ:** `{b['price']} ETB` \n🎁 **ሽልማት:** `{sum(b['prizes'])} ETB` \n━━━━━━━━━━━━━\n"
    
    for i in range(1, b["max"] + 1):
        n = str(i)
        txt += f"{i:02d}.{b['slots'][n]['name'][:4]}🏆 " if n in b["slots"] else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    
    txt += f"\n💰 🥇{b['prizes'][0]} | 🥈{b['prizes'][1]} | 🥉{b['prizes'][2]}\n━━━━━━━━━━━━━\n🕹 @fasil_assistant_bot"
    
    try:
        if b["msg_id"]: bot.edit_message_text(txt, GROUP_ID, b["msg_id"], parse_mode="Markdown")
        else:
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            b["msg_id"] = m.message_id
            bot.pin_chat_message(GROUP_ID, m.message_id)
    except: b["msg_id"] = None
    save_db()

# --- 5. KEYBOARDS ---
def main_kb(uid):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ መረጃ", "🔄 ሰሌዳ ቀይር")
    if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
    return kb

def num_kb(bid, uid):
    kb = telebot.types.InlineKeyboardMarkup(row_width=5)
    b = data["boards"][bid]
    btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"buy_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
    kb.add(*btns)
    return kb

# --- 6. HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"name": None, "wallet": 0, "sel_bid": "1", "step": ""}
    bot.send_message(uid, "👋 ሰላም! እንኳን ወደ ፋሲል ዕጣ በሰላም መጡ።", reply_markup=main_kb(uid))
    
    kb = telebot.types.InlineKeyboardMarkup()
    for k, v in data["boards"].items():
        if v["active"]: kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} ({v['price']} ETB)", callback_data=f"sel_{k}"))
    bot.send_message(uid, "👇 መጫወት የሚፈልጉትን ሰሌዳ ይምረጡ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id); u = data["users"].get(uid)
    if not u: return

    # ሰሌዳ መምረጥ
    if c.data.startswith("sel_"):
        bid = c.data.split("_")[1]
        u["sel_bid"] = bid
        b = data["boards"][bid]
        bot.edit_message_text(f"✅ **{b['name']} ተመርጧል**\n💰 መደብ፦ `{b['price']} ETB` \n━━━━━━━━━━━━━\n🏦 CBE: `1000584461757` \n📱 Telebirr: `0951381356` \n━━━━━━━━━━━━━\n📩 እባክዎ ደረሰኝ ወይም SMS እዚህ ይላኩ።", uid, c.message.message_id, parse_mode="Markdown")

    # ቁጥር መግዛት (The Wallet Logic)
    elif c.data.startswith("buy_"):
        bid = u["sel_bid"]; n = c.data.split("_")[1]
        b = data["boards"][bid]
        
        with data_lock:
            if u["wallet"] >= b["price"]: # የወቅቱን ዋጋ ቼክ ያደርጋል
                if n not in b["slots"]:
                    u["wallet"] -= b["price"] # ብሩን ከዋሌት ይቀንሳል
                    b["slots"][n] = {"name": u["name"], "id": uid}
                    
                    bot.send_message(GROUP_ID, f"🎉 **{u['name']}** ቁጥር **{n}**ን መርጧል! (ቀሪ ዋሌት፦ {u['wallet']} ETB)")
                    refresh_group_board(bid)
                    
                    if u["wallet"] >= b["price"]:
                        bot.edit_message_text(f"✅ ቁጥር {n} ተይዟል! ቀሪ `{u['wallet']} ETB` አለዎት። ይጨምሩ፦", uid, c.message.message_id, reply_markup=num_kb(bid, uid))
                    else:
                        bot.edit_message_text(f"✅ ቁጥር {n} ተይዟል! ዋሌትዎ አልቋል (ቀሪ፦ {u['wallet']} ETB)።", uid, c.message.message_id)
                else: bot.answer_callback_query(c.id, "⚠️ ይቅርታ፣ ይህ ቁጥር አሁን ተይዟል!", show_alert=True)
            else: bot.answer_callback_query(c.id, f"❌ በቂ ብር የለዎትም! (መደብ፦ {b['price']} ETB)", show_alert=True)

    # አድሚን አጽድቅ
    elif c.data.startswith("adm_ok_") and int(uid) == ADMIN_ID:
        t_uid = c.data.split("_")[1]
        u["step"] = f"AMT_{t_uid}"
        bot.send_message(ADMIN_ID, "💵 ለተጠቃሚው የሚገባውን ጠቅላላ የብር መጠን በቁጥር ብቻ ይጻፉ፦")

@bot.message_handler(content_types=['text', 'photo'])
def handle_msgs(m):
    uid = str(m.from_user.id); u = data["users"].get(uid)
    if not u: return

    # አድሚን ብር ሲያስገባ
    if u["step"].startswith("AMT_") and int(uid) == ADMIN_ID:
        t_uid = u["step"].split("_")[1]
        try:
            amt = float(m.text)
            data["users"][t_uid]["wallet"] += amt
            u["step"] = ""
            bot.send_message(GROUP_ID, f"✅ የ **{data['users'][t_uid]['name'] or 'ተጫዋች'}** የ `{amt} ETB` ክፍያ ጸድቋል!")
            
            if not data["users"][t_uid]["name"]:
                data["users"][t_uid]["step"] = "ASK_NAME"
                bot.send_message(t_uid, f"✅ {amt} ETB ዋሌትዎ ላይ ገብቷል! እባክዎ ስምዎን ይጻፉ፦")
            else:
                bot.send_message(t_uid, f"✅ {amt} ETB ዋሌትዎ ላይ ገብቷል! '🕹 ቁጥር ምረጥ' የሚለውን ይጫኑ።")
            save_db(); bot.send_message(ADMIN_ID, "✅ ተፈጽሟል።")
        except: bot.send_message(ADMIN_ID, "❌ ስህተት! ቁጥር ብቻ ያስገቡ።")
        return

    if u["step"] == "ASK_NAME":
        u["name"] = m.text; u["step"] = ""; save_db()
        bot.send_message(uid, f"✅ ተመዝግቧል {m.text}! አሁን ቁጥር መምረጥ ይችላሉ።", reply_markup=main_kb(uid))
        return

    if m.text == "🕹 ቁጥር ምረጥ":
        bid = u["sel_bid"]; b = data["boards"][bid]
        if u["wallet"] >= b["price"]:
            bot.send_message(uid, f"🔢 {b['name']} ቁጥር ይምረጡ (ዋሌት፦ {u['wallet']} ETB)፦", reply_markup=num_kb(bid, uid))
        else: bot.send_message(uid, f"❌ በቂ ብር የለዎትም! (መደብ፦ {b['price']} ETB | ዋሌት፦ {u['wallet']} ETB)")

    elif m.text == "🎫 የእኔ መረጃ":
        bot.send_message(uid, f"👤 ስም፦ {u['name']}\n💰 ዋሌት፦ `{u['wallet']} ETB` \n📍 ሰሌዳ፦ {u['sel_bid']}")

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        kb.add(telebot.types.InlineKeyboardButton("⚙️ የሰሌዳ ዋጋ/ሁኔታ ቀይር", callback_data="adm_manage"))
        bot.send_message(uid, "🛠 የአድሚን መቆጣጠሪያ ክፍል", reply_markup=kb)

    # ደረሰኝ መቀበያ
    if m.content_type == 'photo' or (m.text and len(m.text) > 10):
        if m.chat.id == GROUP_ID: return
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"adm_ok_{uid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"adm_rej_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 አዲስ ደረሰኝ ከ {m.from_user.first_name}", reply_markup=kb)
        if m.content_type == 'photo': bot.forward_message(ADMIN_ID, uid, m.message_id)
        bot.send_message(uid, "📩 ደረሰኝዎ ደርሷል። አድሚኑ እስኪያጸድቅ በትዕግስት ይጠብቁ።")

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
