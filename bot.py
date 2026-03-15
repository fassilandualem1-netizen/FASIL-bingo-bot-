import telebot, json, time, random, re
from flask import Flask
from threading import Thread, Lock

# --- 1. CONFIGURATION ---
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

# --- 3. CORE UTILITIES ---
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

def refresh_group_board(bid):
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
        if b["msg_id"]: bot.edit_message_text(txt, GROUP_ID, b["msg_id"], parse_mode="Markdown")
        else:
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            b["msg_id"] = m.message_id
            bot.pin_chat_message(GROUP_ID, m.message_id)
    except: b["msg_id"] = None
    save_db()

# --- 4. KEYBOARDS ---
def main_menu(uid):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ መረጃ", "🔄 ሰሌዳ ቀይር")
    if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
    return kb

def board_picker_kb():
    kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]: kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} ({v['price']} ETB)", callback_data=f"pick_bd_{k}"))
    return kb

def number_kb(bid):
    kb = telebot.types.InlineKeyboardMarkup(row_width=5)
    b = data["boards"][bid]
    btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"num_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
    kb.add(*btns)
    return kb

# --- 5. HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: data["users"][uid] = {"name": None, "wallet": 0, "tks": 0, "sel_bid": "1", "step": ""}
    bot.send_message(uid, "👋 እንኳን ወደ ፋሲል ልዩ ዕጣ በሰላም መጡ!", reply_markup=main_menu(uid))
    bot.send_message(uid, "👇 መጀመሪያ የሚጫወቱበትን ሰሌዳ ይምረጡ፦", reply_markup=board_picker_kb())

@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(c):
    uid = str(c.from_user.id); u = data["users"].get(uid)
    if not u: return

    # Board Selection
    if c.data.startswith("pick_bd_"):
        bid = c.data.split("_")[-1]
        u["sel_bid"] = bid
        bot.edit_message_text(f"✅ **{data['boards'][bid]['name']} ተመርጧል**\n💰 መደብ፦ {data['boards'][bid]['price']} ETB\n\n🏦 CBE: `1000584461757` \n📱 Telebirr: `0951381356` \n━━━━━━━━━━━━━\n📩 እባክዎ ደረሰኝ ወይም SMS እዚህ ይላኩ።", uid, c.message.message_id, parse_mode="Markdown")

    # Number Selection (Department of Concurrency)
    elif c.data.startswith("num_"):
        bid = u["sel_bid"]; n = c.data.split("_")[-1]
        with data_lock:
            if u["tks"] > 0 and n not in data["boards"][bid]["slots"]:
                data["boards"][bid]["slots"][n] = {"name": u["name"], "id": uid}
                u["tks"] -= 1
                bot.send_message(GROUP_ID, f"🎉 **{u['name']}** ቁጥር **{n}**ን መርጧል! (ቀሪ እጣ፦ {u['tks']})")
                refresh_group_board(bid)
                
                if u["tks"] > 0:
                    bot.edit_message_text(f"✅ ተይዟል! ቀሪ {u['tks']} እጣ አለዎት። ይምረጡ፦", uid, c.message.message_id, reply_markup=number_kb(bid))
                else: bot.edit_message_text("✅ ሁሉንም እጣዎን ጨርሰዋል! መልካም እድል!", uid, c.message.message_id)
            else: bot.answer_callback_query(c.id, "⚠️ ቁጥሩ አሁን ተይዟል ወይም በቂ እጣ የለዎትም!", show_alert=True)

    # Admin Approval Logic
    elif c.data.startswith("adm_ok_") and int(uid) == ADMIN_ID:
        t_uid = c.data.split("_")[-1]
        u_target = data["users"][t_uid]
        u_target["step"] = f"INPUT_AMT_{t_uid}"
        bot.send_message(ADMIN_ID, f"💰 ለ {u_target['name'] or t_uid} ስንት ብር ተላከ? (ቁጥር ብቻ)፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)

@bot.message_handler(content_types=['text', 'photo'])
def handle_all_messages(m):
    uid = str(m.from_user.id); u = data["users"].get(uid)
    if not u: return

    # Registration & Finance Department
    if u["step"].startswith("INPUT_AMT_") and int(uid) == ADMIN_ID:
        t_uid = u["step"].split("_")[-1]
        try:
            amt = float(m.text)
            bid = data["users"][t_uid]["sel_bid"]
            price = data["boards"][bid]["price"]
            new_tks = int(amt // price)
            data["users"][t_uid]["tks"] += new_tks
            data["users"][t_uid]["wallet"] += (amt % price)
            u["step"] = ""
            
            bot.send_message(GROUP_ID, f"✅ የ **{data['users'][t_uid]['name'] or 'ተጫዋች'}** ክፍያ ጸድቋል! {new_tks} እጣ ተሰጥቷል።")
            if not data["users"][t_uid]["name"]:
                data["users"][t_uid]["step"] = "ASK_NAME"
                bot.send_message(t_uid, "✅ ክፍያዎ ጸድቋል! እባክዎ ስምዎን ይጻፉ፦")
            else: bot.send_message(t_uid, f"✅ {new_tks} እጣ ተጨምሯል! '🕹 ቁጥር ምረጥ' የሚለውን ይጫኑ።")
            save_db(); bot.send_message(ADMIN_ID, "✅ በተሳካ ሁኔታ ተመዝግቧል።")
        except: bot.send_message(ADMIN_ID, "❌ እባክዎ ቁጥር ብቻ ያስገቡ!")
        return

    if u["step"] == "ASK_NAME":
        u["name"] = m.text; u["step"] = ""; save_db()
        bot.send_message(uid, f"✅ ተመዝግቧል {m.text}! አሁን ቁጥር መምረጥ ይችላሉ።", reply_markup=main_menu(uid))
        return

    # User Features
    if m.text == "🕹 ቁጥር ምረጥ":
        if u["tks"] > 0: bot.send_message(uid, "🔢 ቁጥር ይምረጡ፦", reply_markup=number_kb(u["sel_bid"]))
        else: bot.send_message(uid, "❌ በቂ እጣ የለዎትም። መጀመሪያ ሰሌዳ መርጠው ደረሰኝ ይላኩ።")

    elif m.text == "🎫 የእኔ መረጃ":
        msg = f"👤 **ስም፦** {u['name'] or 'አልተመዘገበም'}\n💰 **ቀሪ እጣ፦** `{u['tks']}`\n💵 **ዋሌት፦** `{u['wallet']} ETB` \n━━━━━━━━━━━━━\n"
        bot.send_message(uid, msg)

    elif m.text == "🔄 ሰሌዳ ቀይር":
        bot.send_message(uid, "👇 ሊቀይሩት የሚፈልጉትን ሰሌዳ ይምረጡ፦", reply_markup=board_picker_kb())

    # Admin Panel
    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        bot.send_message(uid, "🛠 የአድሚን መቆጣጠሪያ ክፍል በቅርቡ ተጨማሪ ነገሮች ይጨመሩበታል...")

    # Receipt Handling
    if m.content_type == 'photo' or (m.text and len(m.text) > 10):
        if m.chat.id == GROUP_ID: return
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"adm_ok_{uid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"adm_no_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 አዲስ ደረሰኝ ከ {m.from_user.first_name} (ሰሌዳ {u['sel_bid']})", reply_markup=kb)
        if m.content_type == 'photo': bot.forward_message(ADMIN_ID, uid, m.message_id)
        bot.send_message(uid, "📩 ደረሰኝዎ ደርሷል። አድሚኑ እስኪያጸድቅ በትዕግስት ይጠብቁ።")

# --- 6. SERVER & POLLING ---
@app.route('/')
def home(): return "Active"

if __name__ == "__main__":
    load_db()
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
