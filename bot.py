import telebot
import json
import re
from threading import Thread
from flask import Flask

# --- 1. ቅንጅቶች (CONFIG) ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        
DB_CHANNEL_ID = -1003747262103  
CBE_ACCOUNT = "1000584461757"
TELEBIRR_NUMBER = "0951381356"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- 2. ዳታቤዝ (DATABASE) ---
data = {
    "config": {"db_msg_id": None},
    "boards": {
        "1": {"name": "ሰሌዳ 1", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 50},
        "2": {"name": "ሰሌዳ 2", "max": 50, "active": True, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 20}
    },
    "users": {}
}

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
    except: pass

def load_db():
    try:
        chat = bot.get_chat(DB_CHANNEL_ID)
        if chat.pinned_message and "💾 DB_STORAGE" in chat.pinned_message.text:
            raw = chat.pinned_message.text.replace("💾 DB_STORAGE", "").strip()
            data.update(json.loads(raw))
    except: pass

# --- 3. ረዳት ፋንክሽኖች (HELPERS) ---
def filter_sms(text):
    amt_match = re.search(r"(?i)(ETB|ብር)\s*([\d,.]+)", text) or re.search(r"([\d,.]+)\s*(ETB|ብር)", text)
    tid_match = re.search(r"(?i)(ID|Ref):\s*([A-Z0-9]+)", text) or re.search(r"\b([A-Z0-9]{10,})\b", text)
    amount = amt_match.group(2) if amt_match else "ያልታወቀ"
    tid = tid_match.group(1) if tid_match else "ያልታወቀ"
    return amount, tid

def refresh_group_board(bid):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    txt = f"🔥 **{b['name']}** {status}\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{b['price']} ETB` | 🎁 **ሽልማት:** `{sum(b['prizes'])} ETB` \n━━━━━━━━━━━━━\n"
    for i in range(1, b["max"] + 1):
        n = str(i)
        txt += f"{i:02d}.{b['slots'][n]['name'][:4]}🏆 " if n in b["slots"] else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    txt += f"\n💰 🥇{b['prizes'][0]} | 🥈{b['prizes'][1]} | 🥉{b['prizes'][2]}\n━━━━━━━━━━━━━\n🕹 @{bot.get_me().username}"
    try:
        if not b.get("msg_id"):
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            b["msg_id"] = m.message_id
            bot.pin_chat_message(GROUP_ID, m.message_id)
        else: bot.edit_message_text(txt, GROUP_ID, b["msg_id"], parse_mode="Markdown")
    except: pass
    save_db()

# --- 4. የአድሚን ፓነል (ADMIN LOGIC) ---
@bot.callback_query_handler(func=lambda c: c.data.startswith(("adm_", "do_", "set_", "ok_", "no_", "rej_")))
def admin_callbacks(c):
    if c.from_user.id != ADMIN_ID: return
    cmd = c.data.split("_")
    
    if cmd[0] == "adm":
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        if cmd[1] == "reset_main":
            for k in data["boards"]: kb.add(telebot.types.InlineKeyboardButton(f"ሰሌዳ {k} አጽዳ", callback_data=f"do_reset_{k}"))
        elif cmd[1] == "toggle_main":
            for k,v in data["boards"].items(): kb.add(telebot.types.InlineKeyboardButton(f"ሰሌዳ {k} ({'🟢' if v['active'] else '🔴'})", callback_data=f"do_toggle_{k}"))
        bot.edit_message_text("ምርጫዎን ይምረጡ፦", ADMIN_ID, c.message.message_id, reply_markup=kb)

    elif cmd[0] == "do" and cmd[1] == "reset":
        data["boards"][cmd[2]]["slots"] = {}
        save_db()
        bot.answer_callback_query(c.id, "✅ ተረዝቷል!")

    elif cmd[0] == "ok":
        uid, amt = cmd[1], float(cmd[2])
        data["users"][uid]["wallet"] += amt
        save_db()
        bot.send_message(uid, f"✅ ክፍያዎ ተረጋግጧል! {amt} ETB ተጨምሯል።")
        bot.delete_message(ADMIN_ID, c.message.message_id)

# --- 5. የተጠቃሚ ክፍል (USER LOGIC) ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎰 ሰሌዳ ምረጥ", "🕹 ቁጥር ምረጥ", "💰 ዋሌት")
    if m.from_user.id == ADMIN_ID: kb.add("🛠 Admin Panel")
    bot.send_message(uid, f"🌟 **እንኳን ወደ ፋሲል ዕጣ መጡ!**\n\n🏦 CBE: `{CBE_ACCOUNT}`\n📱 Telebirr: `{TELEBIRR_NUMBER}`", reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'text'])
def main_handler(m):
    uid = str(m.from_user.id)
    if m.text == "🛠 Admin Panel" and m.from_user.id == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        kb.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="adm_reset_main"),
               telebot.types.InlineKeyboardButton("🟢/🔴 Toggle On/Off", callback_data="adm_toggle_main"))
        bot.send_message(ADMIN_ID, "🛠 Admin Menu", reply_markup=kb)
    
    elif m.text == "🎰 ሰሌዳ ምረጥ":
        kb = telebot.types.InlineKeyboardMarkup()
        for k, v in data["boards"].items():
            if v["active"]: kb.add(telebot.types.InlineKeyboardButton(f"{v['name']} ({v['price']} ETB)", callback_data=f"sel_{k}"))
        bot.send_message(uid, "ሰሌዳ ይምረጡ፦", reply_markup=kb)

    elif m.text == "💰 ዋሌት":
        bot.send_message(uid, f"💰 ዋሌት፦ {data['users'][uid]['wallet']} ETB")

    elif m.photo or (m.text and len(m.text) > 20): # ደረሰኝ
        bot.send_message(uid, "📩 እያረጋገጥን ነው...")
        amt, tid = filter_sms(m.text if m.text else "")
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton(f"✅ አጽድቅ ({amt})", callback_data=f"ok_{uid}_{amt}"))
        bot.send_message(ADMIN_ID, f"📩 ደረሰኝ ከ {m.from_user.first_name}\nID: {tid}\n`{m.text}`", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("sel_", "n_")))
def user_callbacks(c):
    uid = str(c.from_user.id)
    u = data["users"][uid]
    if c.data.startswith("sel_"):
        u["sel_bid"] = c.data.split("_")[1]
        bot.edit_message_text(f"✅ ሰሌዳ {u['sel_bid']} ተመርጧል! አሁን '🕹 ቁጥር ምረጥ' ይጫኑ።", uid, c.message.message_id)
    elif c.data.startswith("n_"):
        bid = u["sel_bid"]
        num = c.data.split("_")[1]
        if u["wallet"] >= data["boards"][bid]["price"]:
            data["boards"][bid]["slots"][num] = {"name": u["name"], "id": uid}
            u["wallet"] -= data["boards"][bid]["price"]
            refresh_group_board(bid)
            bot.send_message(uid, f"🎉 ቁጥር {num} ተመዝግቧል!")
        else: bot.answer_callback_query(c.id, "❌ በቂ ብር የለም!", show_alert=True)

@app.route('/')
def home(): return "Active"

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
