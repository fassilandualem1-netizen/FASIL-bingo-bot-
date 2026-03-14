import telebot
import re
from flask import Flask
from threading import Thread
import os

# --- ኮንፊገሬሽን ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            
MY_NAME = "FASSIL"
MY_BOT_LINK = "@Fasil_assistant_bot"

bot = telebot.TeleBot(TOKEN)
app = Flask('')

game_data = {
    'price': 20,
    'board': {},                
    'used_txns': set(),
    'users': {}, 
    'current_prizes': {1: 500, 2: 250, 3: 100}, # Default prizes
    'board_msg_id': None
}

@app.route('/')
def home(): return "Fasil Lottery v6 - All Systems Go! 🎰"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def generate_board_text():
    text = f"🎰 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
    text += f"💵 **መደብ:** `{game_data['price']} ETB`\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        if i in game_data['board']:
            name = game_data['board'][i]['display_name']
            text += f"{i:02d}.✅{name} "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 4 == 0: text += "\n"
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🕹 ለመጫወት ደረሰኝ እዚህ ይላኩ 👉 {MY_BOT_LINK}"
    return text

# --- AUTO WINNER FROM BOT ---
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
           f"🔸 CBE: `{1000234567890}`\n"
           f"🔸 Telebirr: `{0912345678}`\n\n"
           f"💰 **መደብ:** {game_data['price']} ETB")
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 የኔ ዎሌት (Wallet)", "🎟 ቁጥር ልምረጥ")
    markup.add("💸 ብር አውጣ (Withdraw)")
    if uid == ADMIN_ID: markup.add("🛠 Admin Panel")
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN PANEL & BOARD ---
@bot.message_handler(commands=['admin', 'board'])
def admin_commands(message):
    if message.from_user.id != ADMIN_ID: return
    if '/admin' in message.text:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Game", callback_data="admin_reset"))
        markup.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="ask_price"))
        markup.add(telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="ask_prizes"))
        bot.send_message(ADMIN_ID, "🛠 **አድሚን ፓነል፦**", reply_markup=markup)
    elif '/board' in message.text:
        msg = bot.send_message(GROUP_ID, generate_board_text(), parse_mode="Markdown")
        game_data['board_msg_id'] = msg.message_id
        bot.pin_chat_message(GROUP_ID, msg.message_id)

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    if call.data == "ask_price":
        game_data['users'][ADMIN_ID] = {'step': 'SET_PRICE'}
        bot.send_message(ADMIN_ID, "💵 አዲሱን የመደብ ዋጋ በቁጥር ብቻ ይጻፉ፦")
    elif call.data == "ask_prizes":
        game_data['users'][ADMIN_ID] = {'step': 'SET_PRIZES'}
        bot.send_message(ADMIN_ID, "🏆 የ 1ኛ፣ 2ኛ፣ 3ኛ ሽልማት በኮማ በመለየት ይጻፉ (ለምሳሌ: 500, 200, 100)፦")
    elif call.data == "admin_reset":
        game_data['board'] = {}; game_data['used_txns'] = set()
        if game_data['board_msg_id']: bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        bot.answer_callback_query(call.id, "♻️ ሰሌዳው ጸድቷል!")
    elif call.data.startswith("app_"):
        _, t_uid, amt, txn = call.data.split("_")
        t_uid = int(t_uid); playable = (float(amt) // 10) * 10
        tks = int(playable // game_data['price']); wlt = playable % game_data['price']
        game_data['used_txns'].add(txn)
        game_data['users'][t_uid] = {'tickets': tks, 'wallet': wlt, 'step': 'ASK_NAME'}
        bot.send_message(t_uid, f"✅ ጸድቋል! {tks} እጣ አለዎት። ሰሌዳው ላይ የሚወጣ ስም ይጻፉ፦")
        bot.edit_message_text(f"✅ የ {amt} ETB ደረሰኝ ጸድቋል", ADMIN_ID, call.message.message_id)
    elif call.data.startswith("wd_ok_"):
        _, _, t_uid, amt = call.data.split("_")
        game_data['users'][int(t_uid)]['pending_withdraw'] = 0
        bot.send_message(int(t_uid), f"✅ {amt} ብር በባንክ ተልኮልዎታል።")
        bot.edit_message_text(f"✅ ተከፍሏል ({amt} ETB)", ADMIN_ID, call.message.message_id)
    elif call.data.startswith("n_"):
        num = int(call.data.split("_")[1])
        if uid not in game_data['users'] or game_data['users'][uid]['tickets'] <= 0: return
        u = game_data['users'][uid]
        game_data['board'][num] = {'display_name': u.get('display_name', 'Player'), 'id': uid}
        u['tickets'] -= 1
        if game_data['board_msg_id']: bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        bot.answer_callback_query(call.id, f"ቁጥር {num} ተመርጧል!")

# --- PRIVATE MESSAGE HANDLER ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = message.from_user.id
    u_data = game_data['users'].get(uid, {'wallet':0, 'tickets':0, 'step':''})

    if message.text == "💰 የኔ ዎሌት (Wallet)":
        bot.send_message(uid, f"📊 **መረጃ:**\n🎟 እጣ: {u_data['tickets']}\n💵 ዋሌት: {u_data['wallet']} ETB\n⏳ Pending: {u_data.get('pending_withdraw', 0)} ETB")
    elif message.text == "💸 ብር አውጣ (Withdraw)":
        if u_data['wallet'] < 50: bot.send_message(uid, "❌ ቢያንስ 50 ብር ያስፈልጋል።"); return
        bot.send_message(uid, "📍 ብሩ የሚላክበትን ባንክና አካውንት ይጻፉ፦")
        game_data['users'][uid]['step'] = 'ASK_BANK'
    elif message.text == "🎟 ቁጥር ልምረጥ":
        if u_data['tickets'] <= 0: bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ።"); return
        markup = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if i not in game_data['board']]
        markup.add(*btns)
        bot.send_message(uid, "ቁጥር ይምረጡ፦", reply_markup=markup)
    elif u_data.get('step') == 'SET_PRICE' and uid == ADMIN_ID:
        game_data['price'] = int(message.text); game_data['users'][uid]['step'] = ''
        bot.send_message(ADMIN_ID, f"✅ ዋጋ ወደ {message.text} ተቀይሯል።")
    elif u_data.get('step') == 'SET_PRIZES' and uid == ADMIN_ID:
        try:
            am = [int(x.strip()) for x in message.text.split(',')]
            game_data['current_prizes'] = {1: am[0], 2: am[1], 3: am[2]}
            game_data['users'][uid]['step'] = ''; bot.send_message(ADMIN_ID, "✅ ሽልማት ተቀምጧል።")
        except: bot.send_message(ADMIN_ID, "ስህተት! እንደዚህ ይጻፉ: 500, 200, 100")
    elif u_data.get('step') == 'ASK_NAME':
        game_data['users'][uid]['display_name'] = message.text; game_data['users'][uid]['step'] = ''
        bot.send_message(uid, "✅ ተመዝግቧል! አሁን ቁጥር ይምረጡ።")
    elif u_data.get('step') == 'ASK_BANK':
        amt = u_data['wallet']; game_data['users'][uid].update({'pending_withdraw': amt, 'wallet': 0, 'step': ''})
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ ተከፍሏል", callback_data=f"wd_ok_{uid}_{amt}"))
        bot.send_message(ADMIN_ID, f"⚠️ **Withdraw!**\n💰 {amt} ETB\n🏦 {message.text}", reply_markup=markup)
        bot.send_message(uid, "✅ ጥያቄው ተልኳል።")
    else:
        res = parse_sms(message.text)
        if res:
            if res['txn'] in game_data['used_txns']: bot.reply_to(message, "❌ ደረሰኙ ተመዝግቧል።"); return
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{res['amount']}_{res['txn']}"))
            bot.send_message(ADMIN_ID, f"📩 **ደረሰኝ!**\n💰 {res['amount']} ETB\n📄 `{res['txn']}`", reply_markup=markup)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
