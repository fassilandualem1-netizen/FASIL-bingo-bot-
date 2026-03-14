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
    'users': {},                # {id: {'tickets': 0, 'wallet': 0, 'display_name': '', 'step': ''}}
    'board_msg_id': None
}

@app.route('/')
def home(): return "Fasil Lottery is Online! 🎰"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- የቢንጎ ሰሌዳ ጽሁፍ ---
def generate_board_text():
    text = f"🎰 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
    text += f"💵 **የአሁኑ መደብ:** `{game_data['price']} ETB`\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        if i in game_data['board']:
            name = game_data['board'][i]['display_name']
            text += f"{i:02d}. ✅ {name}\n"
        else:
            text += f"{i:02d}. ⚪️ ክፍት  "
            if i % 3 == 0: text += "\n"
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += "🕹 ለመሳተፍ @FasilBingoBot ላይ ደረሰኝ ይላኩ!"
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

# --- START (በኢሞጂ ያሸበረቀ) ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    msg = (f"🎰 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
           f"📜 **የጨዋታው ሕግጋት:**\n"
           f"• ትክክለኛ የባንክ SMS ብቻ ይላኩ 📩\n"
           f"• ማጭበርበር ከጨዋታው ያስታግዳል (BAN) 🚫\n"
           f"• የሰርቪስ ክፍያ (ለምሳሌ 2 ብር) ታሳቢ ይደረጋል 💸\n\n"
           f"🏦 **የመክፈያ አካውንቶች (ለመቅዳት ቁጥሩን ይንኩ):**\n"
           f"🔸 CBE: `{1000234567890}` (Fassil A.)\n"
           f"🔸 Telebirr: `{0912345678}` (Fassil A.)\n\n"
           f"💰 **የአሁኑ መደብ:** `{game_data['price']} ETB`\n"
           f"እባክዎ ደረሰኝዎን እዚህ ይላኩ 👇")
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 የኔ ዎሌት (Wallet)", "🎟 ቁጥር ልምረጥ")
    if uid == ADMIN_ID:
        markup.add("🛠 Admin Panel")
        
    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN PANEL ---
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Game", callback_data="admin_reset"))
    markup.add(telebot.types.InlineKeyboardButton("📊 የሁሉንም Wallet እይ", callback_data="admin_view_wallets"))
    bot.send_message(ADMIN_ID, "🛠 **የአድሚን መቆጣጠሪያ ሰሌዳ:**", reply_markup=markup)

# --- SMS HANDLING (Manual Approval + Service Fee Logic) ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = message.from_user.id
    
    if message.text == "💰 የኔ ዎሌት (Wallet)":
        u = game_data['users'].get(uid, {'wallet': 0, 'tickets': 0})
        bot.send_message(uid, f"📊 **የእርስዎ መረጃ:**\n🎟 ቀሪ እጣ: {u['tickets']}\n💵 በዎሌት ያለዎት: {u['wallet']} ብር")
        return

    if uid in game_data['users'] and game_data['users'][uid].get('step') == 'ASK_NAME':
        game_data['users'][uid]['display_name'] = message.text
        game_data['users'][uid]['step'] = 'PICK'
        bot.send_message(uid, f"✅ ተመዝግቧል! ስም፦ {message.text}\nአሁን '🎟 ቁጥር ልምረጥ' ን ይጫኑ።")
        return

    if message.text == "🎟 ቁጥር ልምረጥ" and uid in game_data['users']:
        markup = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if i not in game_data['board']]
        markup.add(*btns)
        bot.send_message(uid, "የሚፈልጉትን ቁጥር ይምረጡ፦", reply_markup=markup)
        return

    res = parse_sms(message.text)
    if res:
        if res['txn'] in game_data['used_txns']:
            bot.reply_to(message, "❌ ይህ ደረሰኝ ተመዝግቧል!")
            return
            
        bot.reply_to(message, "🔍 ደረሰኝዎ ለፋሲል ተልኳል... ⏳ እባክዎ እስኪጸድቅ ይጠብቁ።")
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{res['amount']}_{res['txn']}"))
        markup.add(telebot.types.InlineKeyboardButton("❌ ሰርዝ", callback_data=f"rej_{uid}"))
        
        admin_msg = f"📩 **አዲስ ደረሰኝ መጥቷል!**\n👤 ስም: {message.from_user.first_name}\n💰 መጠን: {res['amount']} ብር\n📄 TXN: `{res['txn']}`"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

# --- CALLBACKS (Approval, Reset, Wallet) ---
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    if call.data.startswith("app_"):
        _, target_uid, amount, txn = call.data.split("_")
        target_uid = int(target_uid)
        amount = float(amount)
        
        # ሒሳብ ስሌት (Service fee logic)
        # ለምሳሌ 32 ብር ከተላከ 30 ብር ለጨዋታ ይውላል
        playable_amount = (amount // 10) * 10 
        tickets = int(playable_amount // game_data['price'])
        wallet = playable_amount % game_data['price']
        
        game_data['used_txns'].add(txn)
        game_data['users'][target_uid] = {'tickets': tickets, 'wallet': wallet, 'txn': txn, 'step': 'ASK_NAME'}
        
        bot.send_message(target_uid, f"✅ ደረሰኝዎ ተረጋግጧል! {tickets} እጣ አለዎት።\n📍 እባክዎ ሰሌዳው ላይ እንዲወጣ የሚፈልጉትን ስም/ስልክ ይጻፉ፦")
        bot.edit_message_text(f"✅ ተፈቅዷል! ({amount} ETB)", ADMIN_ID, call.message.message_id)

    elif call.data == "admin_view_wallets":
        report = "📊 **የተጫዋቾች Wallet ዝርዝር:**\n"
        for user_id, data in game_data['users'].items():
            report += f"👤 {data.get('display_name', 'ያልታወቀ')}: {data['wallet']} ብር\n"
        bot.send_message(ADMIN_ID, report if len(game_data['users']) > 0 else "ምንም ዳታ የለም።")

    elif call.data == "admin_reset":
        game_data['board'] = {}
        game_data['used_txns'] = set()
        bot.answer_callback_query(call.id, "♻️ ሰሌዳው ጸድቷል!")
        if game_data['board_msg_id']:
            bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")

    elif call.data.startswith("n_"):
        uid = call.from_user.id
        num = int(call.data.split("_")[1])
        if uid not in game_data['users'] or game_data['users'][uid]['tickets'] <= 0: return
        
        u = game_data['users'][uid]
        game_data['board'][num] = {'display_name': u['display_name'], 'id': uid}
        u['tickets'] -= 1
        
        bot.edit_message_text(generate_board_text(), GROUP_ID, game_data['board_msg_id'], parse_mode="Markdown")
        bot.send_message(DB_CHANNEL_ID, f"👤 {u['display_name']} ቁጥር {num} ያዘ።\nTXN: {u['txn']}")
        if u['tickets'] == 0: u['step'] = ''
        bot.answer_callback_query(call.id, f"ቁጥር {num} ተመርጧል!")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['admin', 'board', 'setprice'])
def admin_cmds(message):
    if message.from_user.id != ADMIN_ID: return
    if '/board' in message.text:
        msg = bot.send_message(GROUP_ID, generate_board_text(), parse_mode="Markdown")
        game_data['board_msg_id'] = msg.message_id
        bot.pin_chat_message(GROUP_ID, msg.message_id)
    elif '/setprice' in message.text:
        try:
            game_data['price'] = int(message.text.split()[1])
            bot.reply_to(message, f"✅ መደብ ወደ {game_data['price']} ተቀይሯል።")
        except: bot.reply_to(message, "አጠቃቀም፦ /setprice 50")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
