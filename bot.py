import telebot
import re
from flask import Flask
from threading import Thread
import os

# --- ኮንፊገሬሽን ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
DB_CHANNEL_ID = -1003747262103   
GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            
MY_NAME = "FASSIL"

bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- ዳታቤዝ ---
game_data = {
    'price': 20,
    'board': {},                
    'used_txns': set(),
    'pending_approvals': {},    # አድሚኑ እስኪያጸድቅ የሚቆዩ ደረሰኞች
    'users': {},                
    'board_msg_id': None
}

@app.route('/')
def home(): return "Fasil Bingo is Live!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- የቢንጎ ሰሌዳ ጽሁፍ ---
def generate_board_text():
    text = f"🌟 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🌟\n"
    text += f"💵 **መደብ:** {game_data['price']} ETB\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        if i in game_data['board']:
            name = game_data['board'][i]['display_name']
            text += f"{i:02d}. 👤 {name}\n"
        else:
            text += f"{i:02d}. ⚪️ ክፍት  "
            if i % 3 == 0: text += "\n"
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "🕹 ለመሳተፍ @FasilBingoBot ላይ ደረሰኝ ይላኩ!"
    return text

# --- SMS Parser ---
def parse_sms(text):
    t = text.upper()
    amt = re.search(r"ETB\s*([\d,]+\.\d{2})", t) or re.search(r"([\d,]+\.\d{2})\s*ብር", t)
    txn = re.search(r"(DCA[A-Z0-9]+)", t) or re.search(r"(FT[A-Z0-9]+)", t)
    if amt and txn:
        return {"amount": float(amt.group(1).replace(',', '')), "txn": txn.group(1)}
    return None

# --- START ---
@bot.message_handler(commands=['start'])
def start(message):
    msg = (f"👋 **እንኳን ወደ ፋሲል ዕጣ መጡ!**\n\n"
           f"📜 **ሕግጋት:**\n"
           f"• ትክክለኛ ደረሰኝ ብቻ ይላኩ።\n"
           f"• ማጭበርበር ከጨዋታው ያስታግዳል!\n\n"
           f"💰 **መደብ:** {game_data['price']} ብር\n"
           f"ደረሰኝዎን እዚህ ይላኩ 👇")
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- BOARD COMMAND ---
@bot.message_handler(commands=['board'])
def show_board(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(GROUP_ID, generate_board_text(), parse_mode="Markdown")
        game_data['board_msg_id'] = msg.message_id
        bot.pin_chat_message(GROUP_ID, msg.message_id)

# --- SMS HANDLING (Manual Approval) ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = message.from_user.id
    
    # ተጫዋቹ ስም እያስገባ ከሆነ
    if uid in game_data['users'] and game_data['users'][uid].get('step') == 'ASK_NAME':
        game_data['users'][uid]['display_name'] = message.text
        game_data['users'][uid]['step'] = 'PICK'
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎟 ቁጥር ልምረጥ")
        bot.send_message(uid, f"✅ ተመዝግቧል! ስም፦ {message.text}\nአሁን '🎟 ቁጥር ልምረጥ' ን ይጫኑ።", reply_markup=markup)
        return

    # ቁጥር መምረጫ በተን
    if message.text == "🎟 ቁጥር ልምረጥ" and uid in game_data['users']:
        markup = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if i not in game_data['board']]
        markup.add(*btns)
        bot.send_message(uid, "የሚፈልጉትን ቁጥር ይምረጡ፦", reply_markup=markup)
        return

    # ደረሰኝ ሲላክ
    res = parse_sms(message.text)
    if res:
        if res['txn'] in game_data['used_txns']:
            bot.reply_to(message, "❌ ይህ ደረሰኝ ተመዝግቧል!")
            return
            
        bot.reply_to(message, "🔍 ደረሰኝዎ እየታየ ነው... ⏳ እባክዎ ጥቂት ደቂቃ ይጠብቁ።")
        
        # ለአድሚኑ መላክ (Approval)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{res['amount']}_{res['txn']}"))
        markup.add(telebot.types.InlineKeyboardButton("❌ ሰርዝ", callback_data=f"rej_{uid}"))
        
        admin_msg = f"📩 **አዲስ ደረሰኝ መጥቷል!**\n👤 ስም: {message.from_user.first_name}\n💰 መጠን: {res['amount']} ብር\n📄 TXN: `{res['txn']}`"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN ACTIONS & CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data.startswith("app_"): # አድሚኑ ሲያጸድቅ
        _, target_uid, amount, txn = call.data.split("_")
        target_uid = int(target_uid)
        amount = float(amount)
        
        tickets = int(amount // game_data['price'])
        wallet = amount % game_data['price']
        game_data['used_txns'].add(txn)
        game_data['users'][target_uid] = {'tickets': tickets, 'wallet': wallet, 'txn': txn, 'step': 'ASK_NAME'}
        
        bot.send_message(target_uid, f"✅ ደረሰኝዎ ተረጋግጧል! {tickets} እጣ አለዎት።\n📍 እባክዎ ሰሌዳው ላይ እንዲወጣ የሚፈልጉትን ስም/ስልክ ይጻፉ፦")
        bot.edit_message_text(f"✅ ደረሰኙ ጸድቋል! ({amount} ብር)", ADMIN_ID, call.message.message_id)

    elif call.data == "admin_reset":
        game_data['board'] = {}
        game_data['used_txns'] = set()
        bot.answer_callback_query(call.id, "♻️ ሰሌዳው ጸድቷል!")
        if game_data['board_msg_id']:
            bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")

    elif call.data.startswith("n_"): # ተጫዋች ቁጥር ሲመርጥ
        uid = call.from_user.id
        num = int(call.data.split("_")[1])
        if uid not in game_data['users'] or game_data['users'][uid]['tickets'] <= 0: return
        
        u = game_data['users'][uid]
        game_data['board'][num] = {'display_name': u['display_name'], 'id': uid}
        u['tickets'] -= 1
        
        bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        bot.send_message(DB_CHANNEL_ID, f"👤 {u['display_name']} ቁጥር {num} ያዘ።\nTXN: {u['txn']}")
        if u['tickets'] == 0: del game_data['users'][uid]
        bot.answer_callback_query(call.id, f"ቁጥር {num} ተመርጧል!")

# --- ADMIN PANEL COMMAND ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Game", callback_data="admin_reset"))
        bot.send_message(ADMIN_ID, "የአድሚን መቆጣጠሪያ፦", reply_markup=markup)

# --- SET PRICE COMMAND ---
@bot.message_handler(commands=['setprice'])
def set_price(message):
    if message.from_user.id == ADMIN_ID:
        try:
            new_price = int(message.text.split()[1])
            game_data['price'] = new_price
            bot.reply_to(message, f"✅ መደብ ወደ {new_price} ብር ተቀይሯል።")
        except:
            bot.reply_to(message, "አጠቃቀም፦ /setprice 50")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
