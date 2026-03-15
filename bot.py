import telebot
import re
import os
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- 1. CONFIG (እነዚህን እንዳትቀይራቸው) ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = 'https://htdqqcrgzmyegpovnppi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0'

GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. DB FUNCTIONS ---
def get_s():
    res = db.table("game_state").select("value").eq("key", "current_game").execute()
    return res.data[0]['value'] if res.data else {"price": 20, "board": {}, "prizes": [0,0,0], "msg_id": None}

def save_s(s): db.table("game_state").update({"value": s}).eq("key", "current_game").execute()

def get_u(uid):
    uid = str(uid)
    res = db.table("users").select("*").eq("id", uid).execute()
    if res.data: return res.data[0]
    u = {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": ""}
    db.table("users").insert(u).execute()
    return u

def upd_u(uid, data): db.table("users").update(data).eq("id", str(uid)).execute()

# --- 3. THE DESIGNER BOARD (ያሁኑ ልዩ ዲዛይን) ---
def draw_board():
    s = get_s()
    b = s.get('board', {})
    txt = f"🔥 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🔥\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{s['price']} ETB` | 🎁 **ሽልማት:** `{sum(s['prizes'])}` \n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n"
    
    for i in range(1, 101):
        n = str(i)
        if n in b:
            name = b[n]['display_name'][:5]
            txt += f"{i:02d}.{name}🏆 "
        else:
            txt += f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    
    p = s.get('prizes', [0,0,0])
    txt += f"\n💰 **የሽልማት ዝርዝር:**\n🥇 1ኛ: {p[0]} ETB\n🥈 2ኛ: {p[1]} ETB\n🥉 3ኛ: {p[2]} ETB\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n"
    # ያንተ Username እዚህ ጋር ብቻ ነው ያለው
    txt += f"🕹 @Fasil_assistant_bot"
    return txt

def push_board(reset=False):
    s = get_s()
    txt = draw_board()
    try:
        if reset or not s.get('msg_id'):
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            s['msg_id'] = m.message_id
            save_s(s)
            bot.pin_chat_message(GROUP_ID, m.message_id)
        else:
            bot.edit_message_text(txt, GROUP_ID, s['msg_id'], parse_mode="Markdown")
    except: pass

# --- 4. CALLBACKS ---
@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid, s, u = str(c.from_user.id), get_s(), get_u(c.from_user.id)
    
    if c.data.startswith("ok_"):
        _, t_uid, amt = c.data.split("_")
        tks = int(float(amt) // s['price'])
        upd_u(t_uid, {"tickets": tks, "step": "ASK_NAME"})
        bot.send_message(t_uid, "✅ ደረሰኝዎ ጸድቋል! እባክዎ ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)

    elif c.data.startswith("no_"):
        t_uid = c.data.split("_")[1]
        bot.send_message(t_uid, "❌ ይቅርታ የላኩት ደረሰኝ ስህተት ነው ወይም የቆየ ነው።")
        bot.delete_message(ADMIN_ID, c.message.message_id)

    elif c.data.startswith("n_"):
        n = c.data.split("_")[1]
        if u['tickets'] > 0:
            s['board'][n] = {"display_name": u['display_name'], "id": uid}
            save_s(s); upd_u(uid, {"tickets": u['tickets'] - 1})
            push_board() # ሰሌዳውን ያድሳል
            bot.answer_callback_query(c.id, f"ቁጥር {n} ተይዟል!")

    elif c.data == "set_p": upd_u(uid, {"step": "SET_PRICE"}); bot.send_message(uid, "አዲስ ዋጋ ይጻፉ:")
    elif c.data == "set_z": upd_u(uid, {"step": "SET_PRIZES"}); bot.send_message(uid, "ሽልማቶችን በኮማ (1000,500,200):")
    elif c.data == "reset": 
        s['board'] = {}; save_s(s); push_board(True)
        bot.answer_callback_query(c.id, "ሰሌዳው ታድሷል!")

# --- 5. PRIVATE MESSAGES ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private(m):
    uid, u, s = str(m.from_user.id), get_u(m.from_user.id), get_s()

    if m.text == "/start":
        msg = (f"👋 ሰላም {m.from_user.first_name}! ወደ ፋሲል ዕጣ እንኳን መጡ።\n\n"
               f"📜 **ሕግና መመሪያ፦**\n1. መጀመሪያ ክፍያ ይፈጽሙ\n2. የደረሰኝ SMS እዚህ ይላኩ\n3. ሲጸድቅልዎ ስምዎን መዝግበው ቁጥር ይምረጡ\n\n"
               f"💰 **መደብ:** `{s['price']} ETB`\n"
               f"🏦 **CBE:** `1000584461757`\n📱 **Telebirr:** `0951381356`\n\n"
               f"ደረሰኝ እዚህ ይላኩ 👇")
        kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🕹 ቁጥር ምረጥ", "💰 Wallet")
        if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
        bot.send_message(uid, msg, reply_markup=kb, parse_mode="Markdown")

    elif u['step'] == "SET_PRICE":
        s['price'] = int(m.text); save_s(s); upd_u(uid, {"step": ""})
        bot.send_message(uid, "✅ ዋጋ ተቀይሯል!")
    
    elif u['step'] == "SET_PRIZES":
        s['prizes'] = [int(x.strip()) for x in m.text.split(',')]
        save_s(s); upd_u(uid, {"step": ""})
        bot.send_message(uid, "✅ ሽልማት ተቀምጧል!")

    elif u['step'] == "ASK_NAME":
        upd_u(uid, {"display_name": m.text, "step": ""})
        bot.send_message(uid, "✅ ተመዝግቧል! አሁን '🕹 ቁጥር ምረጥ' የሚለውን ይጫኑ።")

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="set_p"))
        kb.add(telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="set_z"))
        kb.add(telebot.types.InlineKeyboardButton("♻️ Reset & New Board", callback_data="reset"))
        bot.send_message(uid, "🛠 የአድሚን መቆጣጠሪያ፦", reply_markup=kb)

    elif m.text == "🕹 ቁጥር ምረጥ":
        if u['tickets'] <= 0: bot.send_message(uid, "❌ እጣ የለዎትም! መጀመሪያ ደረሰኝ ይላኩ።")
        else:
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in s['board']]
            kb.add(*btns)
            bot.send_message(uid, "ቁጥር ይምረጡ:", reply_markup=kb)

    elif m.text == "💰 Wallet":
        bot.send_message(uid, f"📊 **የእርስዎ መረጃ:**\n🎟 እጣ: {u['tickets']}\n💵 ቀሪ ብር: {u['wallet']} ETB")

    # SMS Detection (ብልጥ መለያ)
    elif re.search(r"(FT|DCA|[0-9]{10})", m.text):
        amt_m = re.search(r"(\d+)", m.text)
        amt = int(amt_m.group(1)) if amt_m else 0
        if amt < s['price']:
            bot.send_message(uid, f"⚠️ ይቅርታ! የላኩት ብር ከመደብ ዋጋ ({s['price']} ETB) ያነሰ ነው።")
        else:
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_{amt}"),
                   telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
            bot.send_message(ADMIN_ID, f"📩 **አዲስ ደረሰኝ:**\n👤 ከ: {m.from_user.first_name}\n💰 መጠን: {amt} ETB\n📝 `{m.text[:100]}`", reply_markup=kb)
            bot.send_message(uid, "📩 ደረሰኝዎ ለአድሚን ደርሷል፣ ጥቂት ይጠብቁ።")

# --- 6. SERVER ---
@app.route('/')
def h(): return "Fasil Assistant Bot Online"

if __name__ == "__main__":
    bot.remove_webhook()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
