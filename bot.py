import telebot
import re
import os
import time
import requests
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- ኮንፊገሬሽን ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0"
GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            
RENDER_APP_URL = "https://የአንተ-አፕ-ስም.onrender.com" # ሬንደር ላይ ስትጭነው እዚህ ጋር የአፕህን ሊንክ ቀይረው

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- SUPABASE DB FUNCTIONS ---
def get_game_state():
    try:
        res = supabase.table("game_state").select("value").eq("key", "current_game").execute()
        return res.data[0]['value'] if res.data else {"price": 20, "board": {}, "board_msg_id": None, "current_prizes": {"1": 0, "2": 0, "3": 0}}
    except:
        return {"price": 20, "board": {}, "board_msg_id": None, "current_prizes": {"1": 0, "2": 0, "3": 0}}

def update_game_state(new_state):
    supabase.table("game_state").update({"value": new_state}).eq("key", "current_game").execute()

def get_user(uid):
    uid = str(uid)
    res = supabase.table("users").select("*").eq("id", uid).execute()
    if not res.data:
        new_user = {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": ""}
        supabase.table("users").insert(new_user).execute()
        return new_user
    return res.data[0]

def update_user(uid, data):
    supabase.table("users").update(data).eq("id", str(uid)).execute()

# --- HELPERS ---
def generate_board_text():
    state = get_game_state()
    board = state.get('board', {})
    text = f"🎰 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
    text += f"💵 **የአሁኑ መደብ:** `{state['price']} ETB`\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        s_i = str(i)
        if s_i in board:
            name = board[s_i]['display_name'][:5]
            text += f"{i:02d}.✅{name} "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 4 == 0: text += "\n"
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🕹 ለመሳተፍ @Fasil_assistant_bot"
    return text

def update_group_board():
    state = get_game_state()
    text = generate_board_text()
    try:
        if state.get('board_msg_id'):
            bot.edit_message_text(text, GROUP_ID, state['board_msg_id'], parse_mode="Markdown")
        else:
            msg = bot.send_message(GROUP_ID, text, parse_mode="Markdown")
            state['board_msg_id'] = msg.message_id
            update_game_state(state)
    except:
        msg = bot.send_message(GROUP_ID, text, parse_mode="Markdown")
        state['board_msg_id'] = msg.message_id
        update_game_state(state)

# --- HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.from_user.id)
    state = get_game_state()
    user = get_user(uid)

    if call.data == "admin_reset" and int(uid) == ADMIN_ID:
        state['board'] = {}
        update_game_state(state)
        update_group_board()
        bot.answer_callback_query(call.id, "♻️ ሰሌዳው ታድሷል!")

    elif call.data.startswith("app_"):
        _, t_uid, amt, txn = call.data.split("_")
        num_tks = int(float(amt) // state['price'])
        change = float(amt) % state['price']
        t_user = get_user(t_uid)
        update_user(t_uid, {"tickets": t_user['tickets'] + num_tks, "wallet": t_user['wallet'] + change, "step": "ASK_NAME"})
        bot.send_message(t_uid, "✅ ደረሰኝ ጸድቋል! አሁን ሰሌዳ ላይ የሚወጣ ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, call.message.message_id)

    elif call.data.startswith("n_"):
        num = call.data.split("_")[1]
        if user['tickets'] <= 0: return
        state['board'][num] = {'display_name': user['display_name'], 'id': uid}
        update_game_state(state)
        update_user(uid, {"tickets": user['tickets'] - 1})
        update_group_board()
        bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተመርጧል!")

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = str(message.from_user.id)
    user = get_user(uid)
    state = get_game_state()

    txn = re.search(r"(FT[A-Z0-9]+|DCA[A-Z0-9]+|[0-9][A-Z0-9]{9,})", message.text)
    if txn:
        amt_match = re.search(r"(\d+)\s*(ብር|ETB)", message.text)
        amt = amt_match.group(1) if amt_match else "0"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{amt}_{txn.group(0)}"))
        bot.send_message(ADMIN_ID, f"📩 ደረሰኝ!\n💰 {amt} ETB\n👤 {uid}", reply_markup=markup)
        bot.send_message(uid, "📩 ደረሰኝ ደርሶናል። አድሚን እስኪያጸድቅ ይጠብቁ።")
        return

    if message.text == "/start":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💰 Wallet", "🕹 ቁጥር ምረጥ")
        if int(uid) == ADMIN_ID: markup.add("🛠 Admin Panel")
        bot.send_message(uid, f"እንኳን መጡ! 👋\nመደብ: {state['price']} ብር", reply_markup=markup)

    elif user['step'] == 'ASK_NAME':
        update_user(uid, {"display_name": message.text, "step": ""})
        bot.send_message(uid, "✅ ስም ተመዝግቧል! አሁን ቁጥር ይምረጡ።")

    elif message.text == "🕹 ቁጥር ምረጥ":
        if user['tickets'] <= 0: bot.send_message(uid, "❌ እጣ የሎትም!")
        else:
            markup = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in state['board']]
            markup.add(*btns)
            bot.send_message(uid, "ቁጥር ይምረጡ፦", reply_markup=markup)

# --- ANTI-SLEEP & FLASK ---
@app.route('/')
def home(): return "Bot is Online! 🚀"

def ping_self():
    """ቦቱ እንዳያቀላፋ በየ 10 ደቂቃው ራሱን ፒንግ ያደርጋል"""
    while True:
        try:
            time.sleep(600) # 10 minutes
            requests.get(RENDER_APP_URL)
        except:
            pass

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=ping_self).start()
    bot.infinity_polling()
