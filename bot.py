import telebot
import re
import os
import time
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

# --- Safe DB Initialization ---
try:
    db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase Connection Initialized")
except Exception as e:
    print(f"❌ DB Connection Error: {e}")
    db = None

# --- 2. DATABASE FUNCTIONS (Safe Mode) ---
def get_s():
    try:
        if db:
            res = db.table("game_state").select("value").eq("key", "current_game").execute()
            if res.data: return res.data[0]['value']
    except Exception as e: print(f"DB Error: {e}")
    return {"price": 20, "board": {}, "msg_id": None, "prizes": [0,0,0]}

def save_s(s):
    try:
        if db: db.table("game_state").update({"value": s}).eq("key", "current_game").execute()
    except Exception as e: print(f"DB Save Error: {e}")

def get_u(uid):
    uid = str(uid)
    try:
        if db:
            res = db.table("users").select("*").eq("id", uid).execute()
            if res.data: return res.data[0]
            u = {"id": uid, "tickets": 0, "display_name": "Player", "step": ""}
            db.table("users").insert(u).execute()
            return u
    except: pass
    return {"id": uid, "tickets": 0, "display_name": "Player", "step": ""}

def upd_u(uid, data):
    try:
        if db: db.table("users").update(data).eq("id", str(uid)).execute()
    except: pass

# --- 3. CORE LOGIC ---
def draw_board():
    s = get_s()
    b, p = s.get('board', {}), s.get('prizes', [0,0,0])
    txt = f"🔥 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🔥\n━━━━━━━━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{s['price']} ETB` | 🎁 **ሽልማት:** `{sum(p)}` \n━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        n = str(i)
        txt += f"{i:02d}.{b[n]['display_name'][:5]}🏆 " if n in b else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    txt += f"\n💰 **ሽልማት:** 🥇{p[0]} | 🥈{p[1]} | 🥉{p[2]}\n━━━━━━━━━━━━━━━━━━━━\n🕹 @Fasil_assistant_bot"
    return txt

def refresh_group(new_post=False):
    s, txt = get_s(), draw_board()
    try:
        if new_post or not s.get('msg_id'):
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            s['msg_id'] = m.message_id
            save_s(s)
            bot.pin_chat_message(GROUP_ID, m.message_id)
        else:
            bot.edit_message_text(txt, GROUP_ID, s['msg_id'], parse_mode="Markdown")
    except Exception as e: print(f"Board Error: {e}")

# --- 4. HANDLERS ---
@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid, s, u = str(c.from_user.id), get_s(), get_u(c.from_user.id)
    if c.data.startswith("ok_"):
        _, t_uid, amt = c.data.split("_")
        tks = int(float(amt) // s['price'])
        upd_u(t_uid, {"tickets": tks, "step": "ASK_NAME"})
        bot.send_message(t_uid, f"✅ ጸድቋል! {tks} እጣ አለዎት። ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)
    elif c.data.startswith("no_"):
        bot.send_message(c.data.split("_")[1], "❌ ደረሰኝዎ ውድቅ ተደርጓል!")
        bot.delete_message(ADMIN_ID, c.message.message_id)
    elif c.data.startswith("n_"):
        n = c.data.split("_")[1]
        if u['tickets'] > 0:
            s['board'][n] = {"display_name": u['display_name'], "id": uid}
            save_s(s); upd_u(uid, {"tickets": u['tickets'] - 1}); refresh_group()
            bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል!")
    elif c.data == "adm_price": upd_u(uid, {"step": "SET_PRICE"}); bot.send_message(uid, "አዲስ መደብ ይጻፉ:")
    elif c.data == "adm_prizes": upd_u(uid, {"step": "SET_PRIZES"}); bot.send_message(uid, "ሽልማት በኮማ (500,200,100):")
    elif c.data == "adm_reset":
        s['board'] = {}; save_s(s); refresh_group(new_post=True)
        bot.answer_callback_query(c.id, "ሰሌዳው ታድሷል!")

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(m):
    uid, u, s = str(m.from_user.id), get_u(m.from_user.id), get_s()
    if m.text == "/start":
        kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ እጣ")
        if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
        bot.send_message(uid, f"👋 ሰላም! መደብ: {s['price']} ETB\nCBE: `1000584461757`\nTelebirr: `0951381356` \nደረሰኝ እዚህ ይላኩ 👇", reply_markup=kb)
    elif u['step'] == "SET_PRICE":
        s['price'] = int(m.text); save_s(s); upd_u(uid, {"step": ""}); bot.send_message(uid, "✅ ዋጋ ተቀይሯል!")
    elif u['step'] == "SET_PRIZES":
        try:
            s['prizes'] = [int(x.strip()) for x in m.text.split(',')]
            save_s(s); upd_u(uid, {"step": ""}); bot.send_message(uid, "✅ ሽልማት ተቀምጧል!")
        except: bot.send_message(uid, "❌ ስህተት!")
    elif u['step'] == "ASK_NAME":
        upd_u(uid, {"display_name": m.text, "step": ""}); bot.send_message(uid, "✅ ተመዝግቧል! ቁጥር ይምረጡ።")
    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("💵 ዋጋ", callback_data="adm_price"), telebot.types.InlineKeyboardButton("🏆 ሽልማት", callback_data="adm_prizes"))
        kb.add(telebot.types.InlineKeyboardButton("♻️ Reset & New Board", callback_data="adm_reset"))
        bot.send_message(uid, "🛠 Admin Panel:", reply_markup=kb)
    elif m.text == "🕹 ቁጥር ምረጥ":
        if u['tickets'] <= 0: bot.send_message(uid, "❌ እጣ የለዎትም።")
        else:
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            kb.add(*[telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in s['board']])
            bot.send_message(uid, "ቁጥር ይምረጡ:", reply_markup=kb)
    elif m.text == "🎫 የእኔ እጣ": bot.send_message(uid, f"📊 እጣ: {u['tickets']}")
    elif re.search(r"(FT|DCA|[0-9]{10})", m.text):
        amt = re.search(r"(\d+)", m.text).group(1) if re.search(r"(\d+)", m.text) else str(s['price'])
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_{amt}"), telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 ደረሰኝ ከ {m.from_user.first_name}:\n{m.text}", reply_markup=kb)
        bot.send_message(uid, "📩 ደረሰኝ ተልኳል...")

# --- 5. SERVER & RUN ---
@app.route('/')
def home(): return "Bot is Online"

def run_bot():
    print("🚀 Fasil Bot is starting...")
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=40)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    run_bot()
