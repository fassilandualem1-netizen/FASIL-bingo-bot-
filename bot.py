import telebot
import re
from datetime import datetime
from flask import Flask
from threading import Thread
import os

# --- ኮንፊገሬሽን (Config) ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
DB_CHANNEL_ID = -1003747262103   
GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            
MY_NAME = "FASSIL"               # በደረሰኝ ውስጥ መኖር ያለበት ስም

bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- ዳታቤዝ (በቦቱ ሜሞሪ የሚቆይ) ---
game_data = {
    'price': 20,
    'board': {},                # {ቁጥር: {'name': ስም, 'id': UserID, 'txn': TXN}}
    'used_txns': set(),         # ድግግሞሽ ለመከላከል
    'users': {},                # {'userid': {'tickets': 0, 'wallet': 0, 'txn': ''}}
    'board_msg_id': None
}

@app.route('/')
def home(): return "Gasha Bingo is Online!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- የቢንጎ ሰሌዳ ጽሁፍ ---
def generate_board_text():
    text = f"🎰 **ጋሻ ቢንጎ (መደብ: {game_data['price']} ብር)** 🎰\n"
    text += "————————————————\n"
    for i in range(1, 101):
        if i in game_data['board']:
            text += f"{i}. ✅  "
        else:
            text += f"{i}. {i:02d}  "
        if i % 5 == 0: text += "\n"
    text += "————————————————\n"
    text += "⚠️ ለመሳተፍ ደረሰኝ ለቦቱ @GashaBingoBot በውስጥ ይላኩ።"
    return text

# --- SMS አረጋጋጭ (ሁለቱንም ወገን ያነባል) ---
def parse_sms(text):
    t = text.upper()
    # 1. ያንተ ስም መኖሩን ማረጋገጥ
    if MY_NAME.upper() not in t: return None
    
    # 2. Amount መፈለግ
    amt_match = re.search(r"ETB\s*([\d,]+\.\d{2})", t) or re.search(r"([\d,]+\.\d{2})\s*ብር", t)
    # 3. Transaction ID መፈለግ
    txn_match = re.search(r"(DCA[A-Z0-9]+)", t) or re.search(r"(FT[A-Z0-9]+)", t)

    if amt_match and txn_match:
        amount = float(amt_match.group(1).replace(',', ''))
        txn_id = txn_match.group(1)
        if txn_id in game_data['used_txns']: return "USED"
        return {"amount": amount, "txn": txn_id}
    return None

# --- ትዕዛዞች ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, f"እንኳን መጡ! የአሁኑ መደብ {game_data['price']} ብር ነው።\nእባክዎ የባንክ ደረሰኝ እዚህ ይላኩ።")

@bot.message_handler(commands=['setprice', 'reset', 'board'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    cmd = message.text.split()
    
    if '/setprice' in cmd[0] and len(cmd) > 1:
        game_data['price'] = int(cmd[1])
        bot.reply_to(message, f"✅ መደብ ወደ {cmd[1]} ብር ተቀይሯል።")
    
    elif '/board' in cmd[0]:
        msg = bot.send_message(GROUP_ID, generate_board_text(), parse_mode="Markdown")
        game_data['board_msg_id'] = msg.message_id
        bot.pin_chat_message(GROUP_ID, msg.message_id)
        
    elif '/reset' in cmd[0]:
        game_data['board'] = {}
        game_data['used_txns'] = set()
        bot.reply_to(message, "♻️ ሰሌዳው ጸድቷል!")
        if game_data['board_msg_id']:
            bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")

# --- SMS መቀበያ ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = message.from_user.id
    res = parse_sms(message.text)
    
    if res == "USED":
        bot.reply_to(message, "❌ ይህ ደረሰኝ አስቀድሞ ጥቅም ላይ ውሏል!")
    elif res:
        tickets = int(res['amount'] // game_data['price'])
        wallet = res['amount'] % game_data['price']
        game_data['used_txns'].add(res['txn'])
        game_data['users'][uid] = {'name': message.from_user.first_name, 'tickets': tickets, 'wallet': wallet, 'txn': res['txn']}
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎟 ቁጥር ልምረጥ")
        bot.send_message(uid, f"✅ ተረጋግጧል!\n🎫 እጣ ብዛት: {tickets}\n💰 ተመላሽ: {wallet} ብር", reply_markup=markup)
    
    elif message.text == "🎟 ቁጥር ልምረጥ" and uid in game_data['users']:
        markup = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if i not in game_data['board']]
        markup.add(*btns)
        bot.send_message(uid, "የሚፈልጉትን ቁጥር ይጫኑ:", reply_markup=markup)

# --- ቁጥር ሲመረጥ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("n_"))
def callback_numbers(call):
    uid = call.from_user.id
    num = int(call.data.split("_")[1])
    
    if uid not in game_data['users'] or game_data['users'][uid]['tickets'] <= 0:
        bot.answer_callback_query(call.id, "እጣ የሎትም!")
        return

    if num in game_data['board']:
        bot.answer_callback_query(call.id, "ይህ ቁጥር አሁን ተያዘ! ሌላ ይምረጡ።", show_alert=True)
        return

    # መመዝገብ
    u = game_data['users'][uid]
    game_data['board'][num] = {'name': u['name'], 'id': uid, 'txn': u['txn']}
    u['tickets'] -= 1
    
    # ዳታቤዝ ሪፖርት
    report = f"👤 [{u['name']}](tg://user?id={uid})\n🔢 ቁጥር: {num}\n📄 TXN: `{u['txn']}`"
    bot.send_message(DB_CHANNEL_ID, report, parse_mode="Markdown")
    
    # ሰሌዳ አፕዴት
    if game_data['board_msg_id']:
        try: bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        except: pass

    if u['tickets'] > 0:
        bot.send_message(uid, f"✅ ቁጥር {num} ተይዟል! ቀሪ {u['tickets']} እጣ አለዎት።")
    else:
        bot.send_message(uid, f"✅ ተጠናቀቀ! መልካም ዕድል!")
        del game_data['users'][uid]

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
