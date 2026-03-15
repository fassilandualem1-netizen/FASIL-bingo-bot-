import telebot
import re
import os
import json
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = 'https://htdqqcrgzmyegpovnppi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0'

GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DB WRAPPERS (በጥንቃቄ የተሰሩ) ---
def get_db_state():
    try:
        res = supabase.table("game_state").select("value").eq("key", "current_game").execute()
        if res.data: return res.data[0]['value']
    except Exception as e:
        print(f"DB Error (state): {e}")
    return {"price": 20, "board": {}, "board_msg_id": None, "prizes": [0, 0, 0]}

def save_db_state(state):
    try: supabase.table("game_state").update({"value": state}).eq("key", "current_game").execute()
    except Exception as e: print(f"DB Error (save): {e}")

def get_db_user(uid):
    uid = str(uid)
    try:
        res = supabase.table("users").select("*").eq("id", uid).execute()
        if res.data: return res.data[0]
        user = {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": "", "temp_amt": 0}
        supabase.table("users").insert(user).execute()
        return user
    except Exception as e:
        print(f"DB Error (user): {e}")
        return {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": "", "temp_amt": 0}

def update_db_user(uid, data):
    try: supabase.table("users").update(data).eq("id", str(uid)).execute()
    except Exception as e: print(f"DB Error (update): {e}")

# --- DESIGN & BOARD ---
def generate_board_text():
    state = get_db_state()
    board = state.get('board', {})
    text = f"🎰 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🎰\n━━━━━━━━━━━━━\n"
    text += f"💵 **መደብ:** `{state.get('price')} ETB` | 🏆 **እጣ**\n━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        s_i = str(i)
        if s_i in board:
            name = str(board[s_i].get('display_name', 'Player'))[:5]
            text += f"{i:02d}.{name}🏆🏆🏆🙏👍 "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 3 == 0: text += "\n"
    p = state.get('prizes', [0, 0, 0])
    text += f"\n🎁 **ሽልማቶች:** 1ኛ: {p[0]} | 2ኛ: {p[1]} | 3ኛ: {p[2]}\n"
    text += "━━━━━━━━━━━━━\n🕹 @Fasil_assistant_bot"
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
    except Exception as e:
        msg = bot.send_message(GROUP_ID, text, parse_mode="Markdown")
        state['board_msg_id'] = msg.message_id
        save_db_state(state)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.from_user.id)
    state = get_db_state()
    user = get_db_user(uid)

    try:
        if call.data.startswith("app_"): # Approve
            _, t_uid, amt, txn = call.data.split("_")
            num_tks = int(float(amt) // state['price'])
            update_db_user(t_uid, {"tickets": num_tks, "wallet": float(amt)%state['price'], "step": "ASK_NAME"})
            bot.send_message(t_uid, f"✅ ጸድቋል! {num_tks} እጣ ተሰጥቶዎታል። ስምዎን ይጻፉ፦")
            bot.delete_message(ADMIN_ID, call.message.message_id)

        elif call.data.startswith("rej_"): # Reject
            t_uid = call.data.split("_")[1]
            bot.send_message(t_uid, "❌ ደረሰኝዎ ስህተት ስለሆነ ውድቅ ተደርጓል።")
            bot.delete_message(ADMIN_ID, call.message.message_id)

        elif call.data.startswith("n_"): # Pick Num
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
            save_db_state(state); update_group_board()
            bot.answer_callback_query(call.id, "♻️ ሰሌዳው ታድሷል!")
    except Exception as e: print(f"Callback Error: {e}")

# --- PRIVATE MESSAGES ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = str(message.from_user.id)
    user = get_db_user(uid)
    state = get_db_state()

    if message.text == "/start":
        msg = f"👋 ሰላም! መደብ: {state['price']} ETB።\nደረሰኝ ይላኩ።"
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🕹 ቁጥር ምረጥ", "💰 Wallet", "💸 Withdrawal")
        if int(uid) == ADMIN_ID: markup.add("🛠 Admin Panel")
        bot.send_message(uid, msg, reply_markup=markup)
        return

    # SMS Detection
    txn_match = re.search(r"(FT[A-Z0-9]+|DCA[A-Z0-9]+|[0-9][A-Z0-9]{9,})", message.text)
    if txn_match and user['step'] == "":
        amt_match = re.search(r"(\d+)", message.text)
        amt = amt_match.group(1) if amt_match else str(state['price'])
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{amt}_{txn_match.group(0)}"),
                   telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"rej_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 ደረሰኝ: {amt} ETB", reply_markup=markup)
        bot.send_message(uid, "📩 ደረሰኝ ደርሶናል፣ አድሚን እስኪያጸድቅ ይጠብቁ።")
        return

    # Admin Panel
    if message.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="admin_reset"))
        bot.send_message(uid, "Admin Control", reply_markup=markup)

    # Pick Number Button
    if message.text == "🕹 ቁጥር ምረጥ":
        if user['tickets'] <= 0: bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ።")
        else:
            markup = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in state['board']]
            markup.add(*btns)
            bot.send_message(uid, "ቁጥር ይምረጡ፦", reply_markup=markup)

    if user['step'] == 'ASK_NAME':
        update_db_user(uid, {"display_name": message.text, "step": ""})
        bot.send_message(uid, "✅ ተመዝግቧል! አሁን ቁጥር ይምረጡ።")

# --- AUTO WINNER (Group) ---
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID)
def monitor_winners(message):
    if not message.text: return
    state = get_db_state()
    match = re.search(r"(1ኛ|2ኛ|3ኛ)\s*ዕጣ\D*(\d+)", message.text)
    if match:
        rank, num = match.group(1), match.group(2)
        if num in state['board']:
            winner = state['board'][num]
            bot.send_message(ADMIN_ID, f"🏆 አሸናፊ: {winner['display_name']} (ቁጥር {num})")

# --- SERVER ---
@app.route('/')
def home(): return "Bot is Online"

if __name__ == "__main__":
    bot.remove_webhook()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    print("Bot is running...")
    bot.infinity_polling(timeout=60)
