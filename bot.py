import telebot
import re
import os
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- 1. SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = 'https://htdqqcrgzmyegpovnppi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0'

GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. DATABASE HELPERS ---
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
        user = {"id": uid, "tickets": 0, "display_name": "Player", "step": ""}
        supabase.table("users").insert(user).execute()
        return user
    except: return {"id": uid, "tickets": 0, "display_name": "Player", "step": ""}

def update_db_user(uid, data):
    try: supabase.table("users").update(data).eq("id", str(uid)).execute()
    except: pass

# --- 3. BOARD DESIGN ---
def generate_board_text():
    state = get_db_state()
    board = state.get('board', {})
    text = f"🎰 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🎰\n━━━━━━━━━━━━━\n"
    text += f"💵 **መደብ:** `{state.get('price', 20)} ETB` | 🏆 **እጣ**\n━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        s_i = str(i)
        if s_i in board:
            name = board[s_i]['display_name'][:5]
            text += f"{i:02d}.{name}🏆 "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 3 == 0: text += "\n"
    text += "\n━━━━━━━━━━━━━\n🕹 ለመሳተፍ @Fasil_assistant_bot"
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
            bot.pin_chat_message(GROUP_ID, msg.message_id)
    except:
        msg = bot.send_message(GROUP_ID, text, parse_mode="Markdown")
        state['board_msg_id'] = msg.message_id
        save_db_state(state)

# --- 4. CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.from_user.id)
    state = get_db_state()
    user = get_db_user(uid)

    if call.data.startswith("app_"):
        _, t_uid, amt = call.data.split("_")
        num_tks = int(float(amt) // state.get('price', 20))
        update_db_user(t_uid, {"tickets": num_tks, "step": "ASK_NAME"})
        bot.send_message(t_uid, f"✅ ጸድቋል! {num_tks} እጣ ተሰጥቶዎታል። አሁን ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, call.message.message_id)

    elif call.data.startswith("n_"):
        num = call.data.split("_")[1]
        if user['tickets'] <= 0:
            bot.answer_callback_query(call.id, "❌ እጣ የለዎትም!")
            return
        state['board'][num] = {'display_name': user['display_name'], 'id': uid}
        save_db_state(state)
        update_db_user(uid, {"tickets": user['tickets'] - 1})
        update_group_board()
        bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተይዟል!")

    elif call.data == "admin_reset" and int(uid) == ADMIN_ID:
        state['board'] = {}
        save_db_state(state)
        update_group_board()
        bot.answer_callback_query(call.id, "ሰሌዳው ጸድቷል!")

# --- 5. PRIVATE MESSAGES ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = str(message.from_user.id)
    user = get_db_user(uid)
    state = get_db_state()

    if message.text == "/start":
        msg = (f"👋 **ሰላም {message.from_user.first_name}!** 🎰\n\n"
               f"💰 **መደብ:** {state.get('price')} ብር\n"
               f"🔸 **CBE:** `1000584461757` \n"
               f"🔸 **Telebirr:** `0951381356` \n\n"
               f"ደረሰኝዎን እዚህ ይላኩ 👇")
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ እጣ")
        if int(uid) == ADMIN_ID: markup.add("🛠 Admin Panel")
        bot.send_message(uid, msg, reply_markup=markup, parse_mode="Markdown")
        return

    # SMS Detection
    txn_match = re.search(r"(FT[A-Z0-9]+|DCA[A-Z0-9]+|[0-9][A-Z0-9]{9,})", message.text)
    if txn_match and user['step'] == "":
        amt_match = re.search(r"(\d+)", message.text)
        amt = amt_match.group(1) if amt_match else str(state.get('price'))
        bot.send_message(uid, "📩 ደረሰኝዎ ደርሷል፣ አድሚን እስኪያጸድቅ ይጠብቁ።")
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{amt}"))
        bot.send_message(ADMIN_ID, f"📩 **አዲስ ደረሰኝ:**\n💰 {amt} ETB\n📄 TXN: `{txn_match.group(0)}`", reply_markup=markup)
        return

    if message.text == "🎫 የእኔ እጣ":
        bot.send_message(uid, f"📊 **መረጃ:**\n🎟 ቀሪ እጣ: {user['tickets']}")
    
    elif message.text == "🕹 ቁጥር ምረጥ":
        if user['tickets'] <= 0:
            bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ።")
        else:
            markup = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in state['board']]
            markup.add(*btns)
            bot.send_message(uid, "ቁጥር ይምረጡ፦", reply_markup=markup)

    elif user['step'] == 'ASK_NAME':
        update_db_user(uid, {"display_name": message.text, "step": ""})
        bot.send_message(uid, "✅ ስም ተመዝግቧል! አሁን ቁጥር ይምረጡ።")

    elif message.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="admin_reset"))
        bot.send_message(uid, "የአድሚን መቆጣጠሪያ:", reply_markup=markup)

# --- 6. SERVER ---
@app.route('/')
def home(): return "Bot is Online! 🚀"

if __name__ == "__main__":
    bot.remove_webhook()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling(timeout=60)
