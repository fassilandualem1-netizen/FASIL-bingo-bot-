import telebot
import re
from flask import Flask
from threading import Thread
import os

# --- ኮንፊገሬሽን ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            
MY_BOT_LINK = "@Fasil_assistant_bot"

bot = telebot.TeleBot(TOKEN, threaded=False) # Render ላይ እንዳይጋጭ threaded=False
app = Flask(__name__)

# ዳታቤዝ
game_data = {
    'price': 20,
    'board': {},                
    'used_txns': set(),
    'users': {}, 
    'current_prizes': {1: 500, 2: 250, 3: 100},
    'board_msg_id': None
}

@app.route('/')
def home():
    return "Fasil Bingo Active!"

# --- AUTO WINNER (ከሌላው ቦት የሚመጣ) ---
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID and m.from_user.is_bot)
def auto_winner_detector(message):
    text = message.text
    # ፎቶው ላይ ባለው መሰረት ፊልተር ማድረግ
    first = re.search(r"🥇 1ኛ ዕጣ፦ (\d+)", text)
    second = re.search(r"🥈 2ኛ ዕጣ፦ (\d+)", text)
    third = re.search(r"🥉 3ኛ ዕጣ፦ (\d+)", text)
    
    prizes = game_data['current_prizes']
    results = []
    if first: results.append((1, int(first.group(1))))
    if second: results.append((2, int(second.group(1))))
    if third: results.append((3, int(third.group(1))))

    for rank, num in results:
        if num in game_data['board']:
            winner_uid = game_data['board'][num]['id']
            prize = prizes.get(rank, 0)
            if winner_uid not in game_data['users']: game_data['users'][winner_uid] = {'wallet':0, 'tickets':0}
            game_data['users'][winner_uid]['wallet'] += prize
            bot.send_message(winner_uid, f"🎊 እንኳን ደስ አለዎት! የ {rank}ኛ አሸናፊ በመሆንዎ {prize} ብር ዋሌትዎ ላይ ተጨምሯል!")
            bot.send_message(GROUP_ID, f"🎉 ቁጥር {num} የ {rank}ኛ አሸናፊ ነው! {prize} ETB በዋሌት ተልኳል።")

# --- START MENU ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    msg = (f"🎰 **እንኳን ወደ ፋሲል ዕጣ መጡ!** 🎰\n\n"
           f"🏦 **አካውንቶች (ለመቅዳት ይጫኑ):**\n"
           f"🔸 CBE: `1000234567890`\n"
           f"🔸 Telebirr: `0912345678`\n\n"
           f"💰 **መደብ:** {game_data['price']} ETB")
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 የኔ ዎሌት (Wallet)", "🎟 ቁጥር ልምረጥ")
    markup.add("💸 ብር አውጣ (Withdraw)")
    if uid == ADMIN_ID: markup.add("🛠 Admin Panel")
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN PANEL ---
@bot.callback_query_handler(func=lambda call: call.data == "ask_prizes")
def set_prizes_call(call):
    game_data['users'][ADMIN_ID] = {'step': 'SET_PRIZES'}
    bot.send_message(ADMIN_ID, "🏆 የ 1ኛ፣ 2ኛ፣ 3ኛ ሽልማት በኮማ ይጻፉ (ለምሳሌ: 500, 200, 100)፦")

# (ሌሎች የ SMS እና የስም መቀበያ Logic እዚህ ይገባሉ...)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Flaskን በ Thread አስነሳ
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    # ቦቱን በ infinity_polling አስነሳ
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
