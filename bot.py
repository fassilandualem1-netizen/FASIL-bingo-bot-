import telebot
import re
import os
import time
import requests
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0"
GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            
RENDER_APP_URL = "https://fasil-bingo.onrender.com" 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DB HELPERS ---
def get_db_state():
    try:
        res = supabase.table("game_state").select("value").eq("key", "current_game").execute()
        return res.data[0]['value']
    except:
        return {"price": 20, "board": {}, "board_msg_id": None, "current_prizes": {"1": 0, "2": 0, "3": 0}}

def save_db_state(state):
    supabase.table("game_state").update({"value": state}).eq("key", "current_game").execute()

def get_db_user(uid):
    uid = str(uid)
    res = supabase.table("users").select("*").eq("id", uid).execute()
    if not res.data:
        new_user = {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": "", "temp_amt": 0}
        supabase.table("users").insert(new_user).execute()
        return new_user
    return res.data[0]

def update_db_user(uid, data):
    supabase.table("users").update(data).eq("id", str(uid)).execute()

# --- BOARD DESIGN ---
def generate_board_text():
    state = get_db_state()
    board = state.get('board', {})
    text = f"🎰 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🎰\n"
    text += f"━━━━━━━━━━━━━━━━━━\n"
    text += f"💵 **መደብ:** `{state['price']} ETB` | 🏆 **ዕጣ**\n"
    text += "━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        s_i = str(i)
        if s_i in board:
            name = board[s_i]['display_name'][:5]
            text += f"{i:02d}.{name}✅ "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 5 == 0: text += "\n"
    text += "━━━━━━━━━━━━━━━━━━\n"
    text += f"🕹 ለመሳተፍ @Fasil_assistant_bot"
    return text

def update_group_board():
    state = get_db_state()
    text = generate_board_text()
    try:
        if state.get('board_msg_id'):
            bot.edit_message_text(text, GROUP_ID, state['board_msg_id'], parse_mode="Markdown")
        else:
            msg = bot.send_message(GROUP_ID, text, parse_mode="Markdown")
            state['board_msg_id'] = msg.message_id
            save_db_state(state)
    except:
        msg = bot.send_message(GROUP_ID, text, parse_mode="Markdown")
        state['board_msg_id'] = msg.message_id
        save_db_state(state)

def get_number_markup(state):
    markup = telebot.types.InlineKeyboardMarkup(row_width=5)
    btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in state['board']]
    markup.add(*btns)
    return markup

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.from_user.id)
    state = get_db_state()
    user = get_db_user(uid)

    if call.data == "admin_reset" and int(uid) == ADMIN_ID:
        state['board'] = {}
        save_db_state(state); update_group_board()
        bot.answer_callback_query(call.id, "♻️ ሰሌዳው ጸድቷል!")

    elif call.data == "ask_price" and int(uid) == ADMIN_ID:
        update_db_user(uid, {"step": "SET_PRICE"})
        bot.send_message(uid, "💵 አዲሱን የመደብ ዋጋ በቁጥር ብቻ ይጻፉ፦")

    elif call.data == "ask_prizes" and int(uid) == ADMIN_ID:
        update_db_user(uid, {"step": "SET_PRIZES"})
        bot.send_message(uid, "🏆 ሽልማቶችን በኮማ ይለዩ (ለምሳሌ: 1000, 500, 200)፦")

    elif call.data.startswith("app_"):
        _, t_uid, amt = call.data.split("_")
        num_tks = int(float(amt) // state['price'])
        change = float(amt) % state['price']
        update_db_user(t_uid, {"tickets": num_tks, "wallet": change, "step": "ASK_NAME"})
        bot.send_message(t_uid, f"✅ ደረሰኝዎ ጸድቋል! {num_tks} እጣ ደርሶዎታል።\n\nእባክዎ ሰሌዳ ላይ እንዲወጣ የሚፈልጉትን ስም አሁን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, call.message.message_id)

    elif call.data.startswith("n_"):
        num = call.data.split("_")[1]
        if user['tickets'] <= 0: return
        state['board'][num] = {'display_name': user['display_name'], 'id': uid}
        save_db_state(state); update_db_user(uid, {"tickets": user['tickets'] - 1})
        update_group_board()
        bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተይዟል!")
        u = get_db_user(uid)
        if u['tickets'] > 0:
            bot.send_message(uid, f"ቀሪ {u['tickets']} እጣ አለዎት። ይምረጡ፦", reply_markup=get_number_markup(state))

# --- PRIVATE MESSAGES ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = str(message.from_user.id)
    user = get_db_user(uid)
    state = get_db_state()

    # 1. መጀመሪያ START እና ዋና በተኖች እንዲሰሩ እናደርጋለን
    if message.text == "/start":
        welcome = (f"👋 **ሰላም {message.from_user.first_name}! እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
                   f"📜 **የጨዋታው ሕግጋት:**\n"
                   f"• ትክክለኛ የባንክ SMS ብቻ ይላኩ።\n"
                   f"• የቆየ ደረሰኝ መላክ ከጨዋታው ያስታግዳል።\n\n"
                   f"💰 **ክፍያ መፈጸም ያለባቸው አካውንቶች:**\n"
                   f"🔸 **CBE:** `1000584461757` (Fassil A.)\n"
                   f"🔸 **Telebirr:** `0951381356` (Fassil A.)\n\n"
                   f"💵 **የአሁኑ መደብ:** {state['price']} ብር\n"
                   f"እባክዎ ደረሰኝዎን እዚህ ይላኩ 👇")
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🕹 ቁጥር ምረጥ", "💰 Wallet")
        if int(uid) == ADMIN_ID: markup.add("🛠 Admin Panel")
        bot.send_message(uid, welcome, reply_markup=markup, parse_mode="Markdown")
        return

    if message.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="admin_reset"))
        markup.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="ask_price"))
        markup.add(telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="ask_prizes"))
        bot.send_message(uid, "🛠 **Admin Control Panel**", reply_markup=markup)
        return

    # 2. የአድሚን ስቴፖች (ዋጋና ሽልማት መቀየሪያ)
    if user['step'] == 'SET_PRICE' and int(uid) == ADMIN_ID:
        try:
            state['price'] = int(message.text)
            save_db_state(state); update_db_user(uid, {"step": ""})
            bot.send_message(uid, f"✅ የመደብ ዋጋ ተቀይሯል።"); update_group_board()
        except: bot.send_message(uid, "⚠️ ቁጥር ብቻ ያስገቡ!")
        return

    if user['step'] == 'SET_PRIZES' and int(uid) == ADMIN_ID:
        try:
            p = [int(x.strip()) for x in message.text.split(',')]
            state['current_prizes'] = {"1": p[0], "2": p[1], "3": p[2]}
            save_db_state(state); update_db_user(uid, {"step": ""})
            bot.send_message(uid, f"✅ ሽልማቶች ተቀምጠዋል።")
        except: bot.send_message(uid, "⚠️ በኮማ ይለዩ!")
        return

    # 3. የሌሎች ስራዎች (Wallet, Select Number)
    if message.text == "💰 Wallet":
        u = get_db_user(uid)
        bot.send_message(uid, f"📊 **መረጃ:**\n🎟 እጣ: {u['tickets']}\n💵 ዋሌት: {u['wallet']} ETB")
        return

    if message.text == "🕹 ቁጥር ምረጥ":
        if user['tickets'] <= 0: bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ (ደረሰኝ ይላኩ)።")
        else: bot.send_message(uid, "ቁጥር ይምረጡ፦", reply_markup=get_number_markup(state))
        return

    if user['step'] == 'ASK_NAME':
        update_db_user(uid, {"display_name": message.text, "step": ""})
        bot.send_message(uid, f"✅ ስም ተመዝግቧል! አሁን ቁጥርዎን ይምረጡ፦", reply_markup=get_number_markup(state))
        return

    # 4. ደረሰኝ መቀበያ (ከላይ ካሉት ትዕዛዞች ውጭ የሆነ ነገር ሲላክ)
    if user['step'] == "":
        amt_match = re.search(r"(\d+)", message.text)
        amt = amt_match.group(1) if amt_match else str(state['price'])
        
        bot.send_message(uid, "📩 ደረሰኝዎ ደርሶናል። አድሚን እስኪያረጋግጥ ድረስ እባክዎ በትዕግስት ይጠብቁ።")
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{amt}"))
        bot.send_message(ADMIN_ID, f"📩 **አዲስ ደረሰኝ!**\n\nከ: {message.from_user.first_name}\nመልዕክት: `{message.text}`", reply_markup=markup)

# --- SERVER ---
@app.route('/')
def home(): return "Bot is Online! 🚀"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
