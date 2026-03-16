import telebot
import os
import json
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ዳታ ማከማቻ
data = {
    "users": {},
    "boards": {
        "1": {"name": "ሰሌዳ 1", "price": 50, "max": 100, "active": True, "slots": {}},
        "2": {"name": "ሰሌዳ 2", "price": 100, "max": 50, "active": True, "slots": {}},
        "3": {"name": "ሰሌዳ 3", "price": 200, "max": 25, "active": True, "slots": {}},
        "4": {"name": "ሰሌዳ 4", "price": 300, "max": 20, "active": True, "slots": {}}
    }
}

# --- 2. LOGIC FUNCTIONS ---
def get_user(uid):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"wallet": 0, "name": "ያልታወቀ", "step": "", "sel_bid": "1"}
    return data["users"][uid]

# --- 3. BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(m):
    u = get_user(m.from_user.id)
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🕹 ቁጥር ምረጥ", "💰 ዋሌትና መረጃ")
    if m.from_user.id == ADMIN_ID:
        kb.add("🛠 Admin Panel")
    
    welcome_text = (
        "🌟 እንኳን ወደ Fasil ዕጣ በደህና መጡ! 🌟\n\n"
        "ለመጫወት መጀመሪያ ሰሌዳ ይምረጡ፣ ከዚያ ክፍያ ይፈጽሙ።\n"
        "የባንክ ሂሳብ፦ CBE 1000584461757 / Telebirr 0951381356"
    )
    bot.send_message(m.chat.id, welcome_text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel")
def admin_menu(m):
    if m.from_user.id != ADMIN_ID: return
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="adm_reset"),
           telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="adm_price"))
    bot.send_message(m.chat.id, "የአድሚን መቆጣጠሪያ፦", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🕹 ቁጥር ምረጥ")
def select_board(m):
    kb = telebot.types.InlineKeyboardMarkup(row_width=1)
    for k, v in data["boards"].items():
        if v["active"]:
            kb.add(telebot.types.InlineKeyboardButton(f"🎰 {v['name']} ({v['price']} ETB)", callback_data=f"sel_{k}"))
    bot.send_message(m.chat.id, "እባክዎ መጫወት የሚፈልጉትን ሰሌዳ ይምረጡ፦", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(c):
    uid = str(c.from_user.id)
    u = get_user(uid)

    if c.data.startswith("sel_"):
        bid = c.data.split("_")[1]
        u["sel_bid"] = bid
        bot.edit_message_text(f"✅ {data['boards'][bid]['name']} ተመርጧል። አሁን የደረሰኝ ፎቶ ወይም SMS ይላኩ።", c.message.chat.id, c.message.message_id)

    elif c.data.startswith("approve_"):
        target_id = c.data.split("_")[1]
        u["step"] = f"ADD_CASH_{target_id}"
        bot.send_message(ADMIN_ID, "ስንት ብር ይግባለት? (ቁጥር ብቻ ይላኩ)")

    elif c.data.startswith("num_"):
        bid = u["sel_bid"]
        num = c.data.split("_")[1]
        price = data["boards"][bid]["price"]
        
        if u["wallet"] >= price:
            if num not in data["boards"][bid]["slots"]:
                u["wallet"] -= price
                data["boards"][bid]["slots"][num] = {"name": u["name"], "id": uid}
                bot.answer_callback_query(c.id, "✅ ቁጥሩ ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 አዲስ ምዝገባ!\nሰሌዳ፦ {data['boards'][bid]['name']}\nቁጥር፦ {num}\nስም፦ {u['name']}")
            else:
                bot.answer_callback_query(c.id, "⚠️ ቁጥሩ ተይዟል!", show_alert=True)
        else:
            bot.answer_callback_query(c.id, "❌ በቂ ሂሳብ የለዎትም!", show_alert=True)

@bot.message_handler(content_types=['photo', 'text'])
def handle_all(m):
    uid = str(m.from_user.id)
    u = get_user(uid)

    # አድሚን ብር ሲያስገባ
    if int(uid) == ADMIN_ID and u["step"].startswith("ADD_CASH_"):
        target_id = u["step"].split("_")[2]
        try:
            amt = float(m.text)
            data["users"][target_id]["wallet"] += amt
            u["step"] = "WAIT_NAME_" + target_id
            bot.send_message(target_id, f"✅ {amt} ብር ገብቷል። እባክዎ ስምዎን ይላኩ፦")
            bot.send_message(ADMIN_ID, "ተሳክቷል! ስም እየጠበቅን ነው።")
        except: bot.send_message(ADMIN_ID, "ስህተት! ቁጥር ብቻ ይላኩ።")
        return

    # ተጠቃሚ ስሙን ሲልክ
    if u["step"].startswith("WAIT_NAME"):
        u["name"] = m.text
        u["step"] = ""
        bid = u["sel_bid"]
        b = data["boards"][bid]
        kb = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"num_{i}") for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
        kb.add(*btns)
        bot.send_message(uid, f"ደህና {m.text}! አሁን ቁጥር ይምረጡ፦", reply_markup=kb)
        return

    # ደረሰኝ መቀበያ
    if m.content_type == 'photo' or (m.text and ("FT" in m.text or "DCA" in m.text)):
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 ደረሰኝ ከ {uid}", reply_markup=kb)
        bot.send_message(uid, "እያረጋገጥን ነው፣ እባክዎ 1-5 ደቂቃ ይጠብቁ።")

# --- 4. SERVER FOR RENDER ---
@app.route('/')
def home(): return "Bot is Online"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
