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
        "1": {"name": "ሰሌዳ 1", "max": 100, "active": True, "slots": {}, "msg_id": None, "prizes": [500, 300, 100], "price": 50},
        "2": {"name": "ሰሌዳ 2", "max": 50, "active": True, "slots": {}, "msg_id": None, "prizes": [250, 150, 50], "price": 100},
        "3": {"name": "ሰሌዳ 3", "max": 25, "active": True, "slots": {}, "msg_id": None, "prizes": [100, 50, 20], "price": 200},
        "4": {"name": "ሰሌዳ 4", "max": 20, "active": True, "slots": {}, "msg_id": None, "prizes": [50, 30, 10], "price": 300}
    },
    "users": {}
}

# --- 3. DATABASE & REFRESH ---
def save_db():
    try:
        payload = "💾 DB_STORAGE " + json.dumps(data)
        db_id = data["config"].get("db_msg_id")
        if db_id: bot.edit_message_text(payload, DB_CHANNEL_ID, db_id)
        else:
            m = bot.send_message(DB_CHANNEL_ID, payload)
            data["config"]["db_msg_id"] = m.message_id
    except: pass

def refresh_group(bid):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    txt = f"🔥 **{b['name']}** {status}\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{b['price']} ETB` | 🎁 **ሽልማት:** `{sum(b['prizes'])} ETB` \n━━━━━━━━━━━━━\n"
    
    # ሰሌዳውን በ 3 ተራ ማሳያ
    for i in range(1, b["max"] + 1):
        n = str(i)
        if n in b["slots"]:
            user_name = b["slots"][n]["name"][:5]
            txt += f"{i:02d}.{user_name}🏆 "
        else:
            txt += f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
        
    txt += f"\n💰 🥇{b['prizes'][0]} | 🥈{b['prizes'][1]} | 🥉{b['prizes'][2]}\n━━━━━━━━━━━━━\n🕹 @fasil_assistant_bot"
    
    try:
        if b["msg_id"]:
            bot.edit_message_text(txt, GROUP_ID, b["msg_id"], parse_mode="Markdown")
        else:
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            b["msg_id"] = m.message_id
            bot.pin_chat_message(GROUP_ID, m.message_id)
    except: pass
    save_db()

# --- 4. HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: 
        data["users"][uid] = {"wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    
    kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]:
            kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} - ({v['price']} ETB)", callback_data=f"sel_{k}"))
    
    bot.send_message(uid, f"🌟 **እንኳን ወደ Fasil ዕጣ በደህና መጡ!** 🌟\n\n**ህግ እና ደንብ:**\n1. ደረሰኝ በትክክል ይላኩ\n2. ክፍያ ካረጋገጥን በኋላ ቁጥር መምረጥ ይችላሉ።\n\nቀሪ ሂሳብዎ፦ `{data['users'][uid]['wallet']} ETB`", parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    
    if c.data.startswith("sel_"):
        bid = c.data.split("_")[1]
        data["users"][uid]["sel_bid"] = bid
        b = data["boards"][bid]
        bot.edit_message_text(f"✅ **{b['name']} ተመርጧል!**\n💰 መደብ፦ `{b['price']} ETB` \n🏦 CBE: `1000584461757` | 📱 Telebirr: `0951381356` \n━━━━━━━━━━━━━\n📩 እባክዎ የደረሰኝ ፎቶ ወይም SMS እዚህ ይላኩ።", uid, c.message.message_id, parse_mode="Markdown")

    elif c.data.startswith("approve_") and int(uid) == ADMIN_ID:
        _, t_uid = c.data.split("_")
        data["users"][uid]["step"] = f"WAIT_AMT_{t_uid}"
        bot.send_message(ADMIN_ID, "✍️ እባክዎ የገባውን የብር መጠን በቁጥር ብቻ ይፃፉ፦")

    elif c.data.startswith("reject_") and int(uid) == ADMIN_ID:
        _, t_uid = c.data.split("_")
        data["users"][uid]["step"] = f"WAIT_REJ_{t_uid}"
        bot.send_message(ADMIN_ID, "✍️ ውድቅ የተደረገበትን ምክንያት ይፃፉ (ለምሳሌ፡ ደረሰኙ ልክ አይደለም)፦")

    elif c.data.startswith("num_"):
        bid = data["users"][uid].get("sel_bid")
        num = c.data.split("_")[1]
        price = data["boards"][bid]["price"]
        
        if data["users"][uid]["wallet"] >= price:
            if num not in data["boards"][bid]["slots"]:
                data["users"][uid]["wallet"] -= price
                data["boards"][bid]["slots"][num] = {"name": data["users"][uid]["name"], "id": uid}
                bot.answer_callback_query(c.id, "✅ በተሳካ ሁኔታ ተመዝግበዋል!")
                bot.delete_message(uid, c.message.message_id)
                refresh_group(bid)
            else:
                bot.answer_callback_query(c.id, "⚠️ ይቅርታ ይህ ቁጥር ተይዟል!", show_alert=True)
        else:
            bot.answer_callback_query(c.id, f"❌ ቀሪ ሂሳብዎ አነስተኛ ነው። {price} ብር ያስፈልጋል!", show_alert=True)

@bot.message_handler(content_types=['text', 'photo'])
def handle_all(m):
    uid = str(m.from_user.id)
    u = data["users"].get(uid)
    if not u: return

    # Admin Logic for Approval
    if u.get("step", "").startswith("WAIT_AMT_") and int(uid) == ADMIN_ID:
        target_uid = u["step"].split("_")[2]
        try:
            amt = float(m.text)
            data["users"][target_uid]["wallet"] += amt
            u["step"] = ""
            bot.send_message(target_uid, f"✅ ክፍያዎ ተረጋግጧል! {amt} ETB ዋሌትዎ ላይ ተጨምሯል።\nአሁን ስምዎን ይፃፉ፦")
            data["users"][target_uid]["step"] = "WAIT_NAME"
            bot.send_message(ADMIN_ID, "✅ ተረጋግጧል!"); save_db()
        except: bot.send_message(ADMIN_ID, "⚠️ እባክዎ ቁጥር ብቻ ይፃፉ")
        return

    # User Logic for Name
    if u.get("step") == "WAIT_NAME":
        u["name"] = m.text
        u["step"] = ""
        bid = u.get("sel_bid", "1")
        b = data["boards"][bid]
        kb = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"num_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
        kb.add(*btns)
        bot.send_message(uid, f"ደህና {m.text}! አሁን ከ {b['name']} ቁጥር ይምረጡ፦", reply_markup=kb)
        return

    # Regular Payment Submission
    if m.content_type == 'photo' or (m.text and ("FT" in m.text or "DCA" in m.text)):
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"reject_{uid}"))
        
        if m.content_type == 'photo':
            bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"📩 አዲስ ደረሰኝ ከ {u['name']}", reply_markup=kb)
        else:
            bot.send_message(ADMIN_ID, f"📩 አዲስ SMS ከ {u['name']}:\n`{m.text}`", reply_markup=kb)
        bot.send_message(uid, "📩 ደረሰኝዎ ደርሶናል! እያረጋገጥን ነው እባክዎን ከ1-5 ደቂቃ ይታገሱን።")

# --- 5. RUN ---
if __name__ == "__main__":
    save_db() # Initialize DB
    print("Bot is running...")
    bot.infinity_polling()
