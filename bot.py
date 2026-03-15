import telebot
import re
import os
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- 1. CONFIGURATION (ኮንፊገሬሽን) ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = 'https://htdqqcrgzmyegpovnppi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0'

GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. DATABASE DEPT (Supabase) ---
def get_db_state():
    try:
        res = supabase.table("game_state").select("value").eq("key", "current_game").execute()
        if res.data: return res.data[0]['value']
    except: pass
    return {"price": 20, "board": {}, "board_msg_id": None, "prizes": [0, 0, 0]}

def save_db_state(state):
    try: supabase.table("game_state").update({"value": state}).eq("key", "current_game").execute()
    except: pass

def get_db_user(uid):
    uid = str(uid)
    try:
        res = supabase.table("users").select("*").eq("id", uid).execute()
        if res.data: return res.data[0]
        user = {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": "", "temp_amt": 0}
        supabase.table("users").insert(user).execute()
        return user
    except: return None

def update_db_user(uid, data):
    try: supabase.table("users").update(data).eq("id", str(uid)).execute()
    except: pass

# --- 3. DESIGN DEPT (ሰሌዳ ዲዛይን) ---
def generate_board_text():
    state = get_db_state()
    board = state.get('board', {})
    text = f"🎰 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🎰\n━━━━━━━━━━━━━\n"
    text += f"💵 **መደብ:** `{state.get('price')} ETB` | 🏆 **እጣ**\n━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        s_i = str(i)
        if s_i in board:
            name = board[s_i]['display_name'][:5]
            text += f"{i:02d}.{name}🏆🏆🏆🙏👍 "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 3 == 0: text += "\n"
    
    p = state.get('prizes', [0, 0, 0])
    text += f"\n🎁 **ሽልማቶች:** 1ኛ: {p[0]} | 2ኛ: {p[1]} | 3ኛ: {p[2]}\n"
    text += "━━━━━━━━━━━━━\n🕹 ለመሳተፍ @Fasil_assistant_bot"
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

# --- 4. AUTO-WINNER & GROUP DETECTOR ---
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID)
def group_monitor(message):
    if not message.text: return
    state = get_db_state()
    # "1ኛ ዕጣ፦ 45" የሚሉ ጽሁፎችን ይፈልጋል
    match = re.search(r"(1ኛ|2ኛ|3ኛ)\s*ዕጣ\D*(\d+)", message.text)
    if match:
        rank_str, num = match.group(1), match.group(2)
        rank_idx = 0 if "1ኛ" in rank_str else (1 if "2ኛ" in rank_str else 2)
        prize = state['prizes'][rank_idx]
        
        if num in state['board']:
            winner = state['board'][num]
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton(f"💰 {prize} ETB ክፈል", callback_data=f"pay_{winner['id']}_{prize}_{rank_str}"))
            bot.send_message(ADMIN_ID, f"🏆 **አሸናፊ ተገኝቷል!**\n\n🏅 ደረጃ: {rank_str}\n🔢 ቁጥር: {num}\n👤 ስም: {winner['display_name']}\n💰 ሽልማት: {prize} ETB", reply_markup=markup)

# --- 5. CALLBACKS (ክፍያ፣ ማጽደቅ፣ ቁጥር መምረጥ) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.from_user.id)
    state = get_db_state()
    user = get_db_user(uid)

    if call.data.startswith("pay_"): # አሸናፊ መክፈያ
        _, w_uid, amt, rank = call.data.split("_")
        w_user = get_db_user(w_uid)
        if w_user:
            new_bal = float(w_user['wallet']) + float(amt)
            update_db_user(w_uid, {"wallet": new_bal})
            bot.send_message(w_uid, f"🎊 እንኳን ደስ አለዎት! የ {rank} አሸናፊ በመሆንዎ የ {amt} ብር ሽልማት ዋሌትዎ ላይ ተጨምሯል።")
            bot.edit_message_text(f"✅ {amt} ETB ለ {w_user['display_name']} ተከፍሏል።", ADMIN_ID, call.message.message_id)

    elif call.data.startswith("app_"): # ደረሰኝ ማጽደቅ
        _, t_uid, amt, txn = call.data.split("_")
        num_tks = int(float(amt) // state['price'])
        update_db_user(t_uid, {"tickets": num_tks, "wallet": float(amt)%state['price'], "step": "ASK_NAME"})
        bot.send_message(t_uid, f"✅ ጸድቋል! {num_tks} እጣ ተሰጥቶዎታል። ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, call.message.message_id)

    elif call.data.startswith("rej_"): # ደረሰኝ ውድቅ
        t_uid = call.data.split("_")[1]
        bot.send_message(t_uid, "❌ ደረሰኝዎ ስህተት ስለሆነ ውድቅ ተደርጓል።")
        bot.delete_message(ADMIN_ID, call.message.message_id)

    elif call.data.startswith("n_"): # ቁጥር መምረጥ
        num = call.data.split("_")[1]
        if user['tickets'] <= 0: return
        state['board'][num] = {'display_name': user['display_name'], 'id': uid}
        save_db_state(state); update_db_user(uid, {"tickets": user['tickets'] - 1})
        update_group_board()
        bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተይዟል!")

    elif call.data == "admin_reset":
        state['board'] = {}
        save_db_state(state); update_group_board()
        bot.answer_callback_query(call.id, "♻️ ሰሌዳው ታድሷል!")

    elif call.data == "ask_price":
        update_db_user(uid, {"step": "SET_PRICE"})
        bot.send_message(uid, "💵 አዲሱን የመደብ ዋጋ ይጻፉ፦")

    elif call.data == "ask_prizes":
        update_db_user(uid, {"step": "SET_PRIZES"})
        bot.send_message(uid, "🏆 ሽልማቶችን በኮማ ይለዩ (1000, 500, 200)፦")

# --- 6. PRIVATE MESSAGE HANDLERS ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = str(message.from_user.id)
    user = get_db_user(uid)
    state = get_db_state()

    if message.text == "/start":
        msg = (f"👋 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
               f"💰 **መደብ:** {state['price']} ብር\n"
               f"🔸 **CBE:** `1000584461757` \n🔸 **Telebirr:** `0951381356` \n\n"
               f"ደረሰኝዎን እዚህ ይላኩ 👇")
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🕹 ቁጥር ምረጥ", "💰 Wallet", "💸 Withdrawal")
        if int(uid) == ADMIN_ID: markup.add("🛠 Admin Panel")
        bot.send_message(uid, msg, reply_markup=markup, parse_mode="Markdown")
        return

    # SMS Detection
    txn_match = re.search(r"(FT[A-Z0-9]+|DCA[A-Z0-9]+|[0-9][A-Z0-9]{9,})", message.text)
    if txn_match and user['step'] == "":
        amt_match = re.search(r"(\d+)", message.text)
        amt = amt_match.group(1) if amt_match else str(state['price'])
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{amt}_{txn_match.group(0)}"),
                   telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"rej_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 **አዲስ ደረሰኝ:** {amt} ETB\n`{message.text}`", reply_markup=markup)
        bot.send_message(uid, "📩 ደረሰኝ ደርሶናል፣ አድሚን እስኪያጸድቅ ይጠብቁ።")
        return

    # Admin Logic
    if user['step'] == 'SET_PRICE':
        state['price'] = int(message.text)
        save_db_state(state); update_db_user(uid, {"step": ""})
        bot.send_message(uid, "✅ ዋጋ ተቀይሯል።"); update_group_board()
    
    elif user['step'] == 'SET_PRIZES':
        p = [int(x.strip()) for x in message.text.split(',')]
        state['prizes'] = p
        save_db_state(state); update_db_user(uid, {"step": ""})
        bot.send_message(uid, "✅ ሽልማቶች ተቀምጠዋል።"); update_group_board()

    elif message.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="admin_reset"))
        markup.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="ask_price"))
        markup.add(telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="ask_prizes"))
        bot.send_message(uid, "🛠 **Admin Control**", reply_markup=markup)

    # User Logic
    elif message.text == "💰 Wallet":
        bot.send_message(uid, f"📊 **መረጃ:**\n🎟 እጣ: {user['tickets']}\n💵 ዋሌት: {user['wallet']} ETB")

    elif message.text == "🕹 ቁጥር ምረጥ":
        if user['tickets'] <= 0: bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ።")
        else:
            markup = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in state['board']]
            markup.add(*btns)
            bot.send_message(uid, "ቁጥር ይምረጡ፦", reply_markup=markup)

    elif user['step'] == 'ASK_NAME':
        update_db_user(uid, {"display_name": message.text, "step": ""})
        bot.send_message(uid, "✅ ስም ተመዝግቧል! አሁን ቁጥር ይምረጡ።")

    elif message.text == "💸 Withdrawal":
        if user['wallet'] < 50: bot.send_message(uid, "❌ ቢያንስ 50 ብር ያስፈልጋል።")
        else:
            update_db_user(uid, {"step": "WD_AMT"})
            bot.send_message(uid, f"💰 ዋሌት: {user['wallet']} ETB። መጠን ይጻፉ፦")

    elif user['step'] == 'WD_AMT':
        update_db_user(uid, {"temp_amt": float(message.text), "step": "WD_BANK"})
        bot.send_message(uid, "✅ ብሩ የሚላክበትን ባንክና አካውንት ይጻፉ፦")

    elif user['step'] == 'WD_BANK':
        bot.send_message(ADMIN_ID, f"🏦 **Withdraw!**\n💰 መጠን: {user['temp_amt']} ETB\n👤 ዝርዝር: {message.text}\nID: `{uid}`")
        update_db_user(uid, {"wallet": user['wallet'] - user['temp_amt'], "step": ""})
        bot.send_message(uid, "✅ ጥያቄዎ ለአድሚን ደርሷል።")

# --- 7. SERVER ---
@app.route('/')
def home(): return "Bot Online!"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
