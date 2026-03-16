import telebot
import os
import json
from flask import Flask
from threading import Thread

# --- SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
ADMIN_ID = 8488592165            
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ዳታ ማከማቻ (ለጊዜው በዲክሽነሪ፣ በኋላ ዳታቤዝ መጨመር ይቻላል)
data = {
    "users": {},
    "boards": {
        "1": {"price": 50, "active": True, "slots": {}},
        "2": {"price": 100, "active": True, "slots": {}}
    }
}

@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]:
        data["users"][uid] = {"wallet": 0, "name": m.from_user.first_name, "step": ""}
    
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ ዋሌት")
    if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, "እንኳን ወደ Fasil ዕጣ በደህና መጡ! \nክፍያ ለመፈጸም ደረሰኝ ይላኩ።", reply_markup=kb)

@bot.message_handler(content_types=['photo', 'text'])
def handle_docs(m):
    uid = str(m.from_user.id)
    # አድሚን ክፍያ ሲያጸድቅ
    if int(uid) == ADMIN_ID and data["users"].get(uid, {}).get("step", "").startswith("ADD_CASH_"):
        target_id = data["users"][uid]["step"].split("_")[2]
        try:
            amount = float(m.text)
            data["users"][target_id]["wallet"] += amount
            data["users"][uid]["step"] = ""
            bot.send_message(target_id, f"✅ ሂሳብዎ ተረጋግጧል! {amount} ብር ዋሌትዎ ላይ ገብቷል።")
            bot.send_message(ADMIN_ID, "ተሳክቷል!")
        except:
            bot.send_message(ADMIN_ID, "እባክዎ ቁጥር ብቻ ይላኩ።")
        return

    # ተራ ደንበኛ ደረሰኝ ሲልክ
    if m.content_type == 'photo' or (m.text and "FT" in m.text):
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"reject_{uid}"))
        bot.send_message(ADMIN_ID, f"አዲስ ደረሰኝ ከ {uid}", reply_markup=kb)
        bot.send_message(uid, "ደረሰኝዎ ደርሶናል፣ እያረጋገጥን ነው...")

@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    if c.data.startswith("approve_"):
        uid = c.data.split("_")[1]
        data["users"][str(ADMIN_ID)]["step"] = f"ADD_CASH_{uid}"
        bot.send_message(ADMIN_ID, "ስንት ብር ይግባለት? ቁጥሩን ብቻ ይላኩ፦")

@app.route('/')
def home(): return "Bot is running!"

def run(): app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    Thread(target=run).start()
    bot.infinity_polling()
