import telebot
import re
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import os

# --- ኮንፊገሬሽን ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
DB_CHANNEL_ID = -1003747262103   # ያንተ ዳታቤዝ
GROUP_ID = -1003881429974        # ቢንጎው የሚካሄድበት ግሩፕ
ADMIN_ID = 8488592165            # ያንተ ID
MY_NAME = "Fassil"               # በደረሰኝ ላይ የሚፈለግ ስም

bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- የቦቱ ዳታ መያዣ ---
game_data = {
    'price': 20,                # መነሻ ዋጋ
    'board': {},                # ቁጥር የያዙ ሰዎች {1: {'name': '..', 'id': ..}}
    'users': {},                # የተጫዋቾች Wallet እና ሁኔታ
    'board_msg_id': None        # ግሩፑ ላይ ያለ የሰሌዳ መልዕክት ID
}

# --- WEB SERVER (Render እንዳይዘጋው) ---
@app.route('/')
def home(): return "Gasha Bingo is Online!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- የቢንጎ ሰሌዳ ቴክስት አዘጋጅ ---
def generate_board_text():
    text = f"🎰 **የቢንጎ ሰሌዳ (መደብ: {game_data['price']} ብር)** 🎰\n"
    text += "————————————————\n"
    for i in range(1, 101):
        if i in game_data['board']:
            user = game_data['board'][i]
            text += f"{i}. ✅ {user['name']}  "
        else:
            text += f"{i}. ⚪️  "
        if i % 4 == 0: text += "\n"
    text += "\n————————————————\n⚠️ ለመሳተፍ ደረሰኝ ለቦቱ በውስጥ መስመር ይላኩ።"
    return text

# --- SMS VERIFICATION (CBE & Telebirr) ---
def parse_sms(text):
    text_upper = text.upper()
    # ስም ቼክ (ያንተ ስም መኖሩን)
    if MY_NAME.upper() not in text_upper: return None
    
    # ሰዓት ቼክ (30 ደቂቃ)
    # ማሳሰቢያ፡ በሰርቨር ሰዓት ልዩነት ምክንያት ለጊዜው በ ቴክስት ብቻ እንለየው
    
    # Amount & TXN ID
    amount = re.search(r"ETB\s*([\d,]+\.\d{2})", text) or re.search(r"([\d,]+\.\d{2})\s*ብር", text)
    txn = re.search(r"DCA[A-Z0-9]+", text) or re.search(r"FT[A-Z0-9]+", text)

    if amount and txn:
        val = float(amount.group(1).replace(',', ''))
        return {"amount": val, "txn": txn.group(0)}
    return None

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        welcome = (f"እንኳን ወደ ጋሻ ቢንጎ መጡ! 👋\n\n"
                   f"የአሁኑ መደብ፦ **{game_data['price']} ብር**\n"
                   f"ለመሳተፍ የባንክ SMS እዚህ ይላኩ።")
        bot.send_message(message.chat.id, welcome, parse_mode="Markdown")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['setprice', 'reset', 'board'])
def admin_cmds(message):
    if message.from_user.id != ADMIN_ID: return
    
    cmd = message.text.split()
    if '/setprice' in cmd[0] and len(cmd) > 1:
        game_data['price'] = int(cmd[1])
        bot.reply_to(message, f"✅ የመደብ ዋጋ ወደ {cmd[1]} ብር ተቀይሯል።")
        
    elif '/board' in cmd[0]:
        msg = bot.send_message(GROUP_ID, generate_board_text(), parse_mode="Markdown")
        game_data['board_msg_id'] = msg.message_id
        bot.pin_chat_message(GROUP_ID, msg.message_id)
        
    elif '/reset' in cmd[0]:
        game_data['board'] = {}
        bot.reply_to(message, "♻️ ሰሌዳው በሙሉ ጸድቷል።")
        if game_data['board_msg_id']:
            bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")

# --- SMS & NAME HANDLING ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_all(message):
    uid = message.from_user.id
    
    # ደረሰኝ ከሆነ
    sms_data = parse_sms(message.text)
    if sms_data:
        tickets = int(sms_data['amount'] // game_data['price'])
        wallet = sms_data['amount'] % game_data['price']
        
        game_data['users'][uid] = {
            'name': message.from_user.first_name,
            'tickets': tickets,
            'wallet': wallet,
            'txn': sms_data['txn'],
            'step': 'PICK'
        }
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("ቁጥር ልምረጥ")
        bot.send_message(uid, f"✅ ደረሰኝ ተረጋግጧል!\n🎫 እጣ ብዛት፦ {tickets}\n💰 ዎሌት፦ {wallet} ብር\n\nአሁን 'ቁጥር ልምረጥ' የሚለውን ይጫኑ።", reply_markup=markup)
        return

    # ቁጥር መምረጥ
    if message.text == "ቁጥር ልምረጥ" and uid in game_data['users']:
        markup = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"num_{i}") for i in range(1, 101)]
        markup.add(*btns)
        bot.send_message(uid, "የሚፈልጉትን ቁጥር ይምረጡ፦", reply_markup=markup)

# --- CALLBACK (ቁጥር ሲመረጥ) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("num_"))
def pick_num(call):
    uid = call.from_user.id
    num = int(call.data.split("_")[1])
    
    if uid not in game_data['users'] or game_data['users'][uid]['tickets'] <= 0:
        bot.answer_callback_query(call.id, "መጀመሪያ ይክፈሉ ወይም እጣ አልቆብዎታል።")
        return

    if num in game_data['board']:
        bot.answer_callback_query(call.id, "ይህ ቁጥር ተይዟል! ሌላ ይምረጡ።", show_alert=True)
        return

    # ይመዝገብ
    user = game_data['users'][uid]
    game_data['board'][num] = {'name': user['name'], 'id': uid}
    user['tickets'] -= 1
    
    # ወደ ዳታቤዝ ቻናል መላክ
    db_msg = (f"🎰 **አዲስ ምዝገባ**\n👤 ስም: [{user['name']}](tg://user?id={uid})\n🔢 ቁጥር: {num}\n"
              f"📄 ደረሰኝ: `{user['txn']}`")
    bot.send_message(DB_CHANNEL_ID, db_msg, parse_mode="Markdown")
    
    # ግሩፑ ላይ ያለውን ቦርድ አፕዴት ማድረግ
    if game_data['board_msg_id']:
        try:
            bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        except: pass

    if user['tickets'] > 0:
        bot.send_message(uid, f"✅ ቁጥር {num} ተይዟል! ቀሪ {user['tickets']} እጣ አለዎት። ቀጣይ ቁጥር ይምረጡ።")
    else:
        bot.send_message(uid, f"✅ ቁጥር {num} ተይዟል! ሁሉንም እጣዎች ጨርሰዋል። መልካም ዕድል!")
        del game_data['users'][uid]

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
