import telebot
import re
import os
import time
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = 'https://htdqqcrgzmyegpovnppi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0'

GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            

bot = telebot.TeleBot(TOKEN, threaded=False) # Threaded False ለ Render ይሻላል
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DB HELPERS ---
def get_db_state():
    try:
        res = supabase.table("game_state").select("value").eq("key", "current_game").execute()
        if res.data: return res.data[0]['value']
    except: pass
    return {"price": 20, "board": {}, "board_msg_id": None}

def save_db_state(state):
    try: supabase.table("game_state").update({"value": state}).eq("key", "current_game").execute()
    except: pass

def get_db_user(uid):
    uid = str(uid)
    try:
        res = supabase.table("users").select("*").eq("id", uid).execute()
        if res.data: return res.data[0]
        user = {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": ""}
        supabase.table("users").insert(user).execute()
        return user
    except: return {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": ""}

# --- DESIGN & UPDATE ---
def generate_board_text():
    state = get_db_state()
    board = state.get('board', {})
    text = f"🎰 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🎰\n━━━━━━━━━━━━━\n"
    text += f"💵 **መደብ:** `{state.get('price', 20)} ETB` | 🏆 **እጣ**\n━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        s_i = str(i)
        if s_i in board:
            name = board[s_i]['display_name'][:5]
            text += f"{i:02d}.{name}🏆🙏👍 "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 3 == 0: text += "\n"
    text += "\n━━━━━━━━━━━━━\n🕹 @Fasil_assistant_bot"
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

# --- HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.from_user.id)
    state = get_db_state()
    user = get_db_user(uid)

    if call.data.startswith("app_"):
        _, t_uid, amt = call.data.split("_")
        num_tks = int(float(amt) // state.get('price', 20))
        supabase.table("users").update({"tickets": num_tks, "step": "ASK_NAME"}).eq("id", t_uid).execute()
        bot.send_message(t_uid, "✅ ጸድቋል! ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, call.message.message_id)

    elif call.data == "admin_reset" and int(uid) == ADMIN_ID:
        state['board'] = {}
        save_db_state(state); update_group_board()
        bot.answer_callback_query(call.id, "ጸድቷል!")

    elif call.data.startswith("n_"):
        num = call.data.split("_")[1]
        if user['tickets'] <= 0: return
        state['board'][num] = {'display_name': user['display_name'], 'id': uid}
        save_db_state(state)
        supabase.table("users").update({"tickets": user['tickets'] - 1}).eq("id", uid).execute()
        update_group_board()
        bot.answer_callback_query(call.id, f"ቁጥር {num} ተይዟል!")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    uid = str(message.from_user.id)
    user = get_db_user(uid)
    state = get_db_state()

    if message.text == "/start":
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🕹 ቁጥር ምረጥ", "💰 Wallet")
        if int(uid) == ADMIN_ID: markup.add("🛠 Admin Panel")
        bot.send_message(uid, f"ሰላም! መደብ: {state.get('price')} ብር። ደረሰኝ ይላኩ።", reply_markup=markup)
        return

    if message.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="admin_reset"))
        bot.send_message(uid, "Admin Panel", reply_markup=markup)
        return

    if user['step'] == 'ASK_NAME':
        supabase.table("users").update({"display_name": message.text, "step": ""}).eq("id", uid).execute()
        bot.send_message(uid, "ስም ተመዝግቧል! አሁን ቁጥር ይምረጡ።")
        return

    # Receipt
    if message.chat.type == 'private' and not message.text.startswith("/"):
        amt_match = re.search(r"(\d+)", message.text)
        amt = amt_match.group(1) if amt_match else "20"
        bot.send_message(uid, "📩 ደረሰኝዎ ደርሷል፣ አድሚን እስኪያጸድቅ ይጠብቁ።")
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{amt}"))
        bot.send_message(ADMIN_ID, f"አዲስ ደረሰኝ: {message.text}", reply_markup=markup)

# --- SERVER ---
@app.route('/')
def home(): return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    bot.remove_webhook()
    Thread(target=run_flask).start()
    print("Bot is starting...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
