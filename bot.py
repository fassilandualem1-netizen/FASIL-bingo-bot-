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

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ዳታቤዝ ---
game_data = {
    'price': 20,
    'board': {},                
    'used_txns': set(),
    'users': {}, 
    'current_prizes': {1: 500, 2: 250, 3: 100},
    'board_msg_id': None
}

@app.route('/')
def home(): return "Fasil Lottery v8 - All Fixed! 🎰"

# --- የቁጥር መምረጫ Buttons ---
def get_number_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=5)
    btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if i not in game_data['board']]
    markup.add(*btns)
    return markup

# --- የቢንጎ ሰሌዳ ---
def generate_board_text():
    text = f"🎰 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
    text += f"💵 **የአሁኑ መደብ:** `{game_data['price']} ETB`\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        if i in game_data['board']:
            name = game_data['board'][i]['display_name']
            text += f"{i:02d}.✅{name} "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 4 == 0: text += "\n"
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🕹 ለመሳተፍ ደረሰኝ እዚህ ይላኩ 👉 {MY_BOT_LINK}"
    return text

# --- SMS Parser ---
def parse_sms(text):
    t = text.upper()
    if "FASSIL" not in t: return None
    amt = re.search(r"ETB\s*([\d,]+\.\d{2})", t) or re.search(r"([\d,]+\.\d{2})\s*ብር", t)
    txn = re.search(r"(DCA[A-Z0-9]+)", t) or re.search(r"(FT[A-Z0-9]+)", t)
    if amt and txn:
        return {"amount": float(amt.group(1).replace(',', '')), "txn": txn.group(1)}
    return None

# --- AUTO WINNER DETECTOR (FROM BOT) ---
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID and m.from_user.is_bot)
def auto_winner_detector(message):
    text = message.text
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

# --- START & MENU ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    msg = (f"🎰 **እንኳን ወደ ፋሲል ዕጣ መጡ!** 🎰\n\n"
           f"🏦 **አካውንቶች (ለመቅዳት ይጫኑ):**\n"
           f"🔸 CBE: `1000234567890` (Fassil)\n"
           f"🔸 Telebirr: `0912345678` (Fassil)\n\n"
           f"💰 **መደብ:** {game_data['price']} ETB")
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 የኔ ዎሌት (Wallet)", "🎟 ቁጥር ልምረጥ")
    markup.add("💸 ብር አውጣ (Withdraw)")
    if uid == ADMIN_ID: markup.add("🛠 Admin Panel")
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN PANEL ---
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Game", callback_data="admin_reset"))
    markup.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="ask_price"))
    markup.add(telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="ask_prizes"))
    bot.send_message(ADMIN_ID, "🛠 **አድሚን ፓነል፦**", reply_markup=markup)

@bot.message_handler(commands=['board'])
def post_board(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(GROUP_ID, generate_board_text(), parse_mode="Markdown")
        game_data['board_msg_id'] = msg.message_id
        bot.pin_chat_message(GROUP_ID, msg.message_id)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    if call.data == "ask_price" and uid == ADMIN_ID:
        game_data['users'][ADMIN_ID] = {'step': 'SET_PRICE'}
        bot.send_message(ADMIN_ID, "💵 አዲሱን የመደብ ዋጋ በቁጥር ብቻ ይጻፉ፦")
    elif call.data == "ask_prizes" and uid == ADMIN_ID:
        game_data['users'][ADMIN_ID] = {'step': 'SET_PRIZES'}
        bot.send_message(ADMIN_ID, "🏆 ሽልማት በኮማ ይጻፉ (ለምሳሌ: 1000, 500, 200)፦")
    elif call.data == "admin_reset" and uid == ADMIN_ID:
        game_data['board'] = {}; game_data['used_txns'] = set()
        if game_data['board_msg_id']: bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        bot.answer_callback_query(call.id, "♻️ ሰሌዳው ጸድቷል!")
    elif call.data.startswith("app_"):
        _, t_uid, amt, txn = call.data.split("_")
        t_uid = int(t_uid); tks = int(float(amt) // game_data['price'])
        game_data['used_txns'].add(txn)
        if t_uid not in game_data['users']: game_data['users'][t_uid] = {'wallet': 0, 'tickets': 0}
        game_data['users'][t_uid]['tickets'] += tks
        game_data['users'][t_uid]['step'] = 'ASK_NAME'
        bot.send_message(t_uid, f"✅ ጸድቋል! {tks} እጣ ተጨምሮልዎታል። ሰሌዳ ላይ የሚወጣ ስምዎን ይጻፉ፦")
        bot.edit_message_text(f"✅ የ {amt} ETB ደረሰኝ ጸድቋል", ADMIN_ID, call.message.message_id)
    elif call.data.startswith("n_"):
        num = int(call.data.split("_")[1])
        if uid not in game_data['users'] or game_data['users'][uid]['tickets'] <= 0:
             bot.answer_callback_query(call.id, "❌ እጣ የሎትም!")
             return
        game_data['board'][num] = {'display_name': game_data['users'][uid].get('display_name', 'Player'), 'id': uid}
        game_data['users'][uid]['tickets'] -= 1
        if game_data['board_msg_id']: 
            try: bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
            except: pass
        bot.answer_callback_query(call.id, f"ቁጥር {num} ተመርጧል!")
        if game_data['users'][uid]['tickets'] > 0:
            bot.send_message(uid, f"ቀሪ {game_data['users'][uid]['tickets']} እጣ አለዎት። ይጨምሩ፦", reply_markup=get_number_markup())

# --- PRIVATE MESSAGE HANDLER ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private_msg(message):
    uid = message.from_user.id
    if uid not in game_data['users']: game_data['users'][uid] = {'wallet':0, 'tickets':0, 'step':''}
    u_data = game_data['users'][uid]
    
    if message.text == "💰 የኔ ዎሌት (Wallet)":
        bot.send_message(uid, f"📊 **መረጃ:**\n🎟 እጣ: {u_data['tickets']}\n💵 ዋሌት: {u_data['wallet']} ETB")
    elif message.text == "🎟 ቁጥር ልምረጥ":
        if u_data['tickets'] <= 0: bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ።"); return
        bot.send_message(uid, "እባክዎ ቁጥር ይምረጡ፦", reply_markup=get_number_markup())
    elif u_data.get('step') == 'SET_PRICE':
        game_data['price'] = int(message.text); game_data['users'][uid]['step'] = ''
        bot.send_message(ADMIN_ID, f"✅ የመደብ ዋጋ ወደ {message.text} ተቀይሯል።")
    elif u_data.get('step') == 'SET_PRIZES':
        try:
            am = [int(x.strip()) for x in message.text.split(',')]
            game_data['current_prizes'] = {1: am[0], 2: am[1], 3: am[2]}
            game_data['users'][uid]['step'] = ''; bot.send_message(ADMIN_ID, "✅ የሽልማት መጠን ተቀምጧል።")
        except: bot.send_message(ADMIN_ID, "⚠️ ስህተት! 1000, 500, 200 በሚል ይጻፉ።")
    elif u_data.get('step') == 'ASK_NAME':
        game_data['users'][uid]['display_name'] = message.text; game_data['users'][uid]['step'] = ''
        bot.send_message(uid, f"✅ ስም ተመዝግቧል! አሁን ቁጥር ይምረጡ፦", reply_markup=get_number_markup())
    elif message.text == "💸 ብር አውጣ (Withdraw)":
        if u_data['wallet'] < 50: bot.send_message(uid, "❌ ቢያንስ 50 ብር ሊኖርዎት ይገባል።"); return
        bot.send_message(uid, "📍 ብሩ የሚላክበትን ባንክና አካውንት ይጻፉ፦")
        game_data['users'][uid]['step'] = 'ASK_BANK'
    elif u_data.get('step') == 'ASK_BANK':
        bot.send_message(ADMIN_ID, f"⚠️ **Withdraw Request!**\n💰 {u_data['wallet']} ETB\n🏦 {message.text}\nUID: `{uid}`")
        u_data['wallet'] = 0; u_data['step'] = ''; bot.send_message(uid, "✅ ጥያቄው ለአድሚን ተልኳል።")
    else:
        res = parse_sms(message.text)
        if res:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{res['amount']}_{res['txn']}"))
            bot.send_message(ADMIN_ID, f"📩 **ደረሰኝ!**\n💰 {res['amount']} ETB\n📄 `{res['txn']}`", reply_markup=markup)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
