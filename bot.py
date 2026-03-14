import telebot
import re
import os
import time
import requests
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- 1. ኮንፊገሬሽን ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0"
GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            
RENDER_APP_URL = "https://fasil-bingo.onrender.com" 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. ዳታቤዝ (DB HELPERS) ---
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

# --- 3. ሰሌዳ (BOARD DESIGN) ---
def generate_board_text():
    state = get_db_state()
    board = state.get('board', {})
    text = f"🎰 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ!** 🎰\n\n"
    text += f"💵 **የአሁኑ መደብ:** `{state['price']} ETB` 🏆\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        s_i = str(i)
        if s_i in board:
            name = board[s_i]['display_name'][:6]
            text += f"{i:02d}.{name}✅🏆🙏 "
        else:
            text += f"{i:02d}.⚪️ "
        if i % 3 == 0: text += "\n" # በ 3 ሲሆን ሰፊ ሰሌዳ ይሆናል
    text += "\n━━━━━━━━━━━━━━━━━━━━\n"
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

# --- 4. CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.from_user.id)
    state = get_db_state()
    user = get_db_user(uid)

    if call.data == "admin_reset" and int(uid) == ADMIN_ID:
        state['board'] = {}
        save_db_state(state); update_group_board()
        bot.answer_callback_query(call.id, "♻️ ሰሌዳው ታድሷል!")

    elif call.data.startswith("win_"):
        _, w_uid, amt, rank = call.data.split("_")
        w_user = get_db_user(w_uid)
        update_db_user(w_uid, {"wallet": w_user['wallet'] + int(amt)})
        bot.send_message(w_uid, f"🎊 እንኳን ደስ አለዎት! የ {rank}ኛ አሸናፊ በመሆንዎ የ {amt} ብር ሽልማት ዋሌትዎ ላይ ተደምሯል!")
        bot.edit_message_text(f"✅ ተከፍሏል ({amt} ብር)", ADMIN_ID, call.message.message_id)

    elif call.data.startswith("app_"):
        _, t_uid, amt, txn = call.data.split("_")
        num_tks = int(float(amt) // state['price'])
        change = float(amt) % state['price']
        update_db_user(t_uid, {"tickets": num_tks, "wallet": change, "step": "ASK_NAME"})
        bot.send_message(t_uid, "✅ ደረሰኝ ጸድቋል! አሁን ሰሌዳ ላይ የሚወጣ ስምዎን ይጻፉ፦")
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

# --- 5. PRIVATE MESSAGES (ADMIN & USER) ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message):
    uid = str(message.from_user.id)
    user = get_db_user(uid)
    state = get_db_state()

    # ሀ. ዋና ዋና ቁልፎች (Main Buttons)
    if message.text == "/start":
        welcome = (f"👋 **እንኳን ወደ ፋሲል ዕጣ በደህና መጡ! 🎰**\n\n"
                   f"💵 **የአሁኑ መደብ:** {state['price']} ብር\n"
                   f"አሁን ደረሰኝዎን እዚህ ይላኩ 👇")
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💰 Wallet", "🕹 ቁጥር ምረጥ")
        markup.add("💸 ብር አውጣ (Withdraw)")
        if int(uid) == ADMIN_ID: markup.add("🛠 Admin Panel")
        bot.send_message(uid, welcome, reply_markup=markup, parse_mode="Markdown")
        return

    elif message.text == "💰 Wallet":
        u = get_db_user(uid)
        bot.send_message(uid, f"📊 **መረጃ:**\n🎟 እጣ: {u['tickets']}\n💵 ዋሌት: {u['wallet']} ETB")
        return

    elif message.text == "🕹 ቁጥር ምረጥ":
        if user['tickets'] <= 0: bot.send_message(uid, "❌ መጀመሪያ እጣ ይግዙ (ደረሰኝ ይላኩ)።")
        else: bot.send_message(uid, "ቁጥር ይምረጡ፦", reply_markup=get_number_markup(state))
        return

    # ለ. ደረሰኝ ማጣሪያ (Receipt Check)
    txn = re.search(r"(FT[A-Z0-9]+|DCA[A-Z0-9]+|[0-9][A-Z0-9]{9,})", message.text)
    if txn:
        amt_match = re.search(r"(\d+)\s*(ብር|ETB)", message.text) or re.search(r"(ብር|ETB)\s*(\d+)", message.text)
        amt = amt_match.group(1) if amt_match else "0"
        if float(amt) < state['price']:
            bot.send_message(uid, f"❌ የላኩት መጠን ({amt} ብር) ከመደቡ ያነሰ ነው።")
            return
        bot.send_message(uid, "📩 ደረሰኝዎ ደርሶናል። አድሚን እስኪያጸድቅ ይጠብቁ።")
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"app_{uid}_{amt}_{txn.group(0)}"))
        bot.send_message(ADMIN_ID, f"📩 **አዲስ ደረሰኝ!**\n💰 {amt} ETB\n📄 TXN: `{txn.group(0)}`", reply_markup=markup)
        return

    # ሐ. የስም ምዝገባ
    if user['step'] == 'ASK_NAME':
        update_db_user(uid, {"display_name": message.text, "step": ""})
        bot.send_message(uid, "✅ ስም ተመዝግቧል! አሁን ቁጥርዎን ይምረጡ፦", reply_markup=get_number_markup(state))
        return

    # መ. Admin Panel ተግባራት (Settings)
    if message.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("♻️ Reset Board", callback_data="admin_reset"))
        markup.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="ask_price"))
        markup.add(telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="ask_prizes"))
        bot.send_message(uid, "🛠 **Admin Control Panel**", reply_markup=markup)
        return

    # ሌሎች (Withdraw, etc.)
    elif message.text == "💸 ብር አውጣ (Withdraw)":
        if user['wallet'] < 50: bot.send_message(uid, "❌ ብር ለማውጣት ቢያንስ 50 ብር ያስፈልጋል።")
        else:
            update_db_user(uid, {"step": "WD_AMT"})
            bot.send_message(uid, f"💰 ዋሌትዎ: {user['wallet']} ETB። ማውጣት የሚፈልጉትን መጠን ይጻፉ፦")

    # ምንም ትዕዛዝ ሳይሆን ዝም ብሎ ለሚላክ መልዕክት
    elif user['step'] == "":
        bot.send_message(uid, "⚠️ ይቅርታ፣ የላኩት መልዕክት ትክክለኛ የባንክ SMS አይመስልም። እባክዎ ሙሉውን መልዕክት ኮፒ አድርገው ይላኩ።")

# --- 6. SERVER & PING ---
@app.route('/')
def home(): return "Fasil Bingo Online! 🚀"

def ping_self():
    while True:
        try: time.sleep(600); requests.get(RENDER_APP_URL)
        except: pass

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    Thread(target=ping_self).start()
    bot.infinity_polling()
