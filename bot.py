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
    'board': {},                # {ቁጥር: {'display_name': '...', 'id': ..}}
    'used_txns': set(),
    'users': {},                # {id: {'tickets': 0, 'wallet': 0, 'step': '', 'temp_txn': ''}}
    'banned': set(),
    'board_msg_id': None
}

@app.route('/')
def home(): return "Fasil Bingo is Live!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- ሰሌዳ አዘገጃጀት (ስም እንዲወጣበት) ---
def generate_board_text():
    text = f"🌟 **እንኳን ወደ ፋሲል ዕጣ መጡ!** 🌟\n"
    text += f"💵 **የአሁኑ መደብ:** {game_data['price']} ETB\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        if i in game_data['board']:
            name = game_data['board'][i]['display_name']
            text += f"{i:02d}. 👤 {name}\n" # ስሙን በዝርዝር ያሳያል
        else:
            text += f"{i:02d}. ⚪️ ክፍት  "
            if i % 3 == 0: text += "\n"
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "🕹 ለመጫወት @FasilBingoBot ላይ ደረሰኝ ይላኩ!"
    return text

# --- SMS Parser ---
def parse_sms(text):
    t = text.upper()
    if MY_NAME.upper() not in t: return None
    amt = re.search(r"ETB\s*([\d,]+\.\d{2})", t) or re.search(r"([\d,]+\.\d{2})\s*ብር", t)
    txn = re.search(r"(DCA[A-Z0-9]+)", t) or re.search(r"(FT[A-Z0-9]+)", t)
    if amt and txn:
        return {"amount": float(amt.group(1).replace(',', '')), "txn": txn.group(1)}
    return None

# --- START (ሕግና መመሪያ) ---
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id in game_data['banned']:
        bot.send_message(message.chat.id, "🚫 እርስዎ ከዚህ ጨዋታ ታግደዋል!")
        return
        
    msg = (f"👋 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
           f"📜 **የጨዋታው ሕግጋት:**\n"
           f"1️⃣ ትክክለኛ የባንክ SMS ብቻ ይላኩ።\n"
           f"2️⃣ የቆየ ወይም የተጭበረበረ ደረሰኝ መላክ **ከጨዋታው ያስታግዳል (BAN)!**\n"
           f"3️⃣ ክፍያ መፈጸም ያለባቸው አካውንቶች፦\n"
           f"   🔸 CBE: `1000XXXXXXXX` (Fassil A.)\n"
           f"   🔸 Telebirr: `09XXXXXXXX` (Fassil A.)\n\n"
           f"💰 **የአሁኑ መደብ:** {game_data['price']} ብር\n"
           f"አሁን ደረሰኝዎን እዚህ ይላኩ 👇")
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 የኔ ዎሌት (Wallet)", "🎟 ቁጥር ልምረጥ")
    if message.from_user.id == ADMIN_ID:
        markup.add("🛠 Admin Panel")
        
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN PANEL ---
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Game", callback_data="admin_reset"))
    markup.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="admin_price"))
    bot.send_message(ADMIN_ID, "የአድሚን መቆጣጠሪያ፦", reply_markup=markup)

# --- SMS HANDLING ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_sms(message):
    uid = message.from_user.id
    
    if message.text == "💰 የኔ ዎሌት (Wallet)":
        bal = game_data['users'].get(uid, {}).get('wallet', 0)
        tks = game_data['users'].get(uid, {}).get('tickets', 0)
        bot.send_message(uid, f"📊 **የእርስዎ መረጃ:**\n🎟 ቀሪ እጣ: {tks}\n💵 በዎሌት ያለዎት: {bal} ብር")
        return

    # ስም እየተጠባበቅን ከሆነ
    if uid in game_data['users'] and game_data['users'][uid].get('step') == 'ASK_NAME':
        game_data['users'][uid]['display_name'] = message.text
        game_data['users'][uid]['step'] = 'PICK'
        bot.send_message(uid, f"✅ ተመዝግቧል! ስም፦ {message.text}\nአሁን '🎟 ቁጥር ልምረጥ' የሚለውን ይጫኑ።")
        return

    res = parse_sms(message.text)
    if res:
        bot.send_message(uid, "🔍 ቆይ... ደረሰኝዎን እያረጋገጥኩ ነው... ⏳")
        if res['txn'] in game_data['used_txns']:
            bot.send_message(uid, "❌ ይህ ደረሰኝ ተመዝግቧል! ማጭበርበር ለ BAN ያጋልጣል።")
            return
        
        tickets = int(res['amount'] // game_data['price'])
        wallet = res['amount'] % game_data['price']
        game_data['used_txns'].add(res['txn'])
        
        game_data['users'][uid] = {
            'tickets': tickets, 
            'wallet': wallet, 
            'txn': res['txn'], 
            'step': 'ASK_NAME'
        }
        bot.send_message(uid, f"✅ ተረጋግጧል! {tickets} እጣ ደርሶዎታል።\n\n📍 እባክዎ በሰሌዳው ላይ እንዲወጣ የሚፈልጉትን **ስም ወይም ስልክ** ይጻፉ፦")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "admin_reset" and call.from_user.id == ADMIN_ID:
        game_data['board'] = {}
        game_data['used_txns'] = set()
        bot.answer_callback_query(call.id, "ሰሌዳው ጸድቷል!")
        if game_data['board_msg_id']:
            bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
            
    elif call.data.startswith("n_"):
        uid = call.from_user.id
        num = int(call.data.split("_")[1])
        if uid not in game_data['users'] or game_data['users'][uid]['tickets'] <= 0: return
        
        u = game_data['users'][uid]
        game_data['board'][num] = {'display_name': u['display_name'], 'id': uid}
        u['tickets'] -= 1
        
        # ሰሌዳ አፕዴት
        bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        bot.send_message(DB_CHANNEL_ID, f"👤 {u['display_name']} ቁጥር {num} ያዘ።\nTXN: {u['txn']}")
        
        if u['tickets'] == 0: del game_data['users'][uid]
        bot.answer_callback_query(call.id, f"ቁጥር {num} ተመርጧል!")

# --- አሂድ ---
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
