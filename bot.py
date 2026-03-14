import telebot
import re
from flask import Flask
from threading import Thread
import os

# --- ኮንፊገሬሽን ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

game_data = {
    'price': 20,
    'board': {},                
    'used_txns': set(),
    'users': {}, 
    'current_prizes': {1: 0, 2: 0, 3: 0}, # አድሚን እስኪሞላው 0 ነው
    'board_msg_id': None
}

@app.route('/')
def home(): return "Fasil Lottery v11 - Final Master 🎰"

# --- HELPERS ---
def get_number_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=5)
    btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if i not in game_data['board']]
    markup.add(*btns)
    return markup

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
    text += f"🕹 ለመሳተፍ ደረሰኝ እዚህ ይላኩ 👉 @Fasil_assistant_bot"
    return text

# --- AUTO WINNER DETECTOR ---
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID and m.from_user.is_bot)
def auto_winner_detector(message):
    text = message.text
    first = re.search(r"🥇 1ኛ ዕጣ፦ (\d+)", text)
    second = re.search(r"🥈 2ኛ ዕጣ፦ (\d+)", text)
    third = re.search(r"🥉 3ኛ ዕጣ፦ (\d+)", text)
    
    results = []
    if first: results.append((1, int(first.group(1))))
    if second: results.append((2, int(second.group(1))))
    if third: results.append((3, int(third.group(1))))

    for rank, num in results:
        if num in game_data['board']:
            winner_uid = game_data['board'][num]['id']
            # አድሚን የወሰነውን የሽልማት መጠን መውሰድ
            prize_to_ask = game_data['current_prizes'].get(rank, 0)
            
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(f"✅ የ {prize_to_ask} ብር ሽልማት አጽድቅ", callback_data=f"win_{winner_uid}_{prize_to_ask}_{rank}"))
            bot.send_message(ADMIN_ID, f"🏆 **አሸናፊ ተገኝቷል!**\n🎖 {rank}ኛ ዕጣ (ቁጥር {num})\n👤 አሸናፊ ID: `{winner_uid}`\n💰 የተወሰነው ሽልማት: {prize_to_ask} ETB\n\nይህን ብር ዋሌቱ ላይ ልደምር?", reply_markup=markup)

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    # ሽልማት ማጽደቅ
    if call.data.startswith("win_"):
        _, w_uid, amt, rank = call.data.split("_")
        w_uid = int(w_uid); amt = int(amt)
        if w_uid not in game_data['users']: game_data['users'][w_uid] = {'wallet':0, 'tickets':0}
        game_data['users'][w_uid]['wallet'] += amt
        bot.send_message(w_uid, f"🎊 እንኳን ደስ አለዎት! የ {rank}ኛ አሸናፊ በመሆንዎ የ {amt} ብር ሽልማት ዋሌትዎ ላይ ተደምሯል!")
        bot.edit_message_text(f"✅ ለ {w_uid} የ {amt} ብር ሽልማት ተልኳል", ADMIN_ID, call.message.message_id)
        bot.send_message(GROUP_ID, f"🎉 የ {rank}ኛ ዕጣ አሸናፊ ሽልማታቸው በዋሌት ተልኳል!")

    # ደረሰኝ ማጽደቅ
    elif call.data.startswith("app_"):
        _, t_uid, amt, txn = call.data.split("_")
        t_uid = int(t_uid); amt_val = float(amt)
        num_tks = int(amt_val // game_data['price'])
        change = amt_val % game_data['price']
        if t_uid not in game_data['users']: game_data['users'][t_uid] = {'wallet': 0, 'tickets': 0}
        game_data['users'][t_uid]['tickets'] += num_tks
        game_data['users'][t_uid]['wallet'] += change
        game_data['users'][t_uid]['step'] = 'ASK_NAME'
        bot.send_message(t_uid, f"✅ ደረሰኝ ጸድቋል!\n🎟 እጣ፡ {num_tks}\n💵 ትርፍ ብር፡ {change} ETB ዋሌትዎ ላይ አለ።\n\nእባክዎ ሰሌዳ ላይ የሚወጣ ስምዎን ይጻፉ፦")
        bot.edit_message_text(f"✅ ደረሰኝ ጸድቋል ({amt} ETB)", ADMIN_ID, call.message.message_id)

    # አድሚን በተኖች
    elif call.data == "ask_price" and uid == ADMIN_ID:
        game_data['users'][ADMIN_ID]['step'] = 'SET_PRICE'
        bot.send_message(ADMIN_ID, "💵 አዲሱን የመደብ ዋጋ በቁጥር ብቻ ይጻፉ፦")
    elif call.data == "ask_prizes" and uid == ADMIN_ID:
        game_data['users'][ADMIN_ID]['step'] = 'SET_PRIZES'
        bot.send_message(ADMIN_ID, "🏆 የ 1ኛ፣ 2ኛ፣ 3ኛ ሽልማት በኮማ ይጻፉ (ለምሳሌ: 500, 300, 100)፦")
    elif call.data == "admin_reset" and uid == ADMIN_ID:
        game_data['board'] = {}; game_data['used_txns'] = set()
        if game_data['board_msg_id']: bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        bot.answer_callback_query(call.id, "♻️ Game Reset!")

    # ቁጥር መምረጥ
    elif call.data.startswith("n_"):
        num = int(call.data.split("_")[1])
        if uid not in game_data['users'] or game_data['users'][uid]['tickets'] <= 0: return
        game_data['board'][num] = {'display_name': game_data['users'][uid].get('display_name', 'Player'), 'id': uid}
        game_data['users'][uid]['tickets'] -= 1
        if game_data['board_msg_id']:
            try: bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
            except: pass
        bot.answer_callback_query(call.id, f"ቁጥር {num} ተመርጧል!")
        if game_data['users'][uid]['tickets'] > 0:
            bot.send_message(uid, f"ቀሪ {game_data['users'][uid]['tickets']} እጣ አለዎት። ይምረጡ፦", reply_markup=get_number_markup())

# --- PRIVATE MESSAGES ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = message.from_user.id
    if uid not in game_data['users']: game_data['users'][uid] = {'wallet':0, 'tickets':0, 'step':''}
    u_data = game_data['users'][uid]

    if message.text == "🛠 Admin Panel" and uid == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Game", callback_data="admin_reset"))
        markup.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="ask_price"))
        markup.add(telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="ask_prizes"))
        bot.send_message(ADMIN_ID, "🛠 **አድሚን ፓነል፦**", reply_markup=markup)

    elif u_data['step'] == 'SET_PRIZES' and uid == ADMIN_ID:
        try:
            p = [int(x.strip()) for x in message.text.split(',')]
            game_data['current_prizes'] = {1: p[0], 2: p[1], 3: p[2]}
            u_data['step'] = ''
            bot.send_message(ADMIN_ID, f"✅ ሽልማት ተቀምጧል፦\n1ኛ: {p[0]}\n2ኛ: {p[1]}\n3ኛ: {p[2]}")
        except: bot.send_message(ADMIN_ID, "⚠️ ስህተት! እንደዚህ ይጻፉ፡ 500, 300, 100")

    elif message.text == "💰 የኔ ዎሌት (Wallet)":
        bot.send_message(uid, f"📊 **መረጃ:**\n🎟 ቀሪ እጣ: {u_data['tickets']}\n💵 ዋሌት: {u_data['wallet']} ETB")

    elif message.text == "💸 ብር አውጣ (Withdraw)":
        if u_data['wallet'] < 50:
            bot.send_message(uid, f"❌ ቢያንስ 50 ብር ያስፈልጋል። ዋሌትዎ፡ {u_data['wallet']} ETB")
            return
        bot.send_message(uid, f"💰 መጠን፡ {u_data['wallet']} ETB\n\nማውጣት የሚፈልጉትን መጠን በቁጥር ብቻ ይጻፉ፦")
        u_data['step'] = 'WD_AMOUNT'

    elif u_data['step'] == 'WD_AMOUNT':
        try:
            val = float(message.text)
            if val > u_data['wallet']: bot.send_message(uid, "❌ በቂ ገንዘብ የሎትም!")
            else:
                u_data['temp_amt'] = val
                bot.send_message(uid, "✅ አሁን ብሩ የሚላክበትን ባንክና አካውንት ይጻፉ፦")
                u_data['step'] = 'WD_BANK'
        except: bot.send_message(uid, "⚠️ ቁጥር ብቻ ይጻፉ።")

    elif u_data['step'] == 'WD_BANK':
        amt = u_data['temp_amt']
        bot.send_message(ADMIN_ID, f"⚠️ **Withdraw Request!**\n💰 መጠን: {amt} ETB\n🏦 አካውንት: {message.text}\nUser: `{uid}`")
        u_data['wallet'] -= amt
        u_data['step'] = ''
        bot.send_message(uid, "✅ ጥያቄዎ ለአድሚን ተልኳል።")

    elif u_data['step'] == 'ASK_NAME':
        u_data['display_name'] = message.text; u_data['step'] = ''
        bot.send_message(uid, "✅ ስም ተመዝግቧል! አሁን ቁጥር ይምረጡ፦", reply_markup=get_number_markup())

    elif message.text == "🎟 ቁጥር ልምረጥ":
        if u_data['tickets'] <= 0: bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ።"); return
        bot.send_message(uid, "ቁጥር ይምረጡ፦", reply_markup=get_number_markup())

    elif "/start" in message.text:
        msg = (f"🎰 **እንኳን ወደ ፋሲል ዕጣ መጡ!** 🎰\n\n"
               f"🏦 **አካውንቶች:**\n"
               f"🔸 CBE: `1000234567890` (Fassil)\n"
               f"🔸 Telebirr: `0912345678` (Fassil)\n\n"
               f"💰 **መደብ:** {game_data['price']} ETB")
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💰 የኔ ዎሌት (Wallet)", "🎟 ቁጥር ልምረጥ")
        markup.add("💸 ብር አውጣ (Withdraw)")
        if uid == ADMIN_ID: markup.add("🛠 Admin Panel")
        bot.send_message(uid, msg, reply_markup=markup, parse_mode="Markdown")
    else:
        # SMS Check
        txn = re.search(r"FT[A-Z0-9]+", message.text) or re.search(r"DCA[A-Z0-9]+", message.text)
        if txn:
            amt_match = re.search(r"(\d+)\s*ብር", message.text) or re.search(r"ETB\s*(\d+)", message.text)
            amt = amt_match.group(1) if amt_match else "0"
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{amt}_{txn.group(0)}"))
            bot.send_message(ADMIN_ID, f"📩 **ደረሰኝ!**\n💰 {amt} ETB\n📄 TXN: `{txn.group(0)}`", reply_markup=markup)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
