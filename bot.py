import telebot
import re
import os
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- CONFIG ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = 'https://htdqqcrgzmyegpovnppi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0'

GROUP_ID = -1003881429974        
ADMIN_ID = 8488592165            

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DB CORE ---
def get_s():
    res = db.table("game_state").select("value").eq("key", "current_game").execute()
    return res.data[0]['value'] if res.data else {"price": 20, "board": {}, "prizes": [0,0,0], "msg_id": None}

def save_s(s): db.table("game_state").update({"value": s}).eq("key", "current_game").execute()

def get_u(uid):
    uid = str(uid)
    res = db.table("users").select("*").eq("id", uid).execute()
    if res.data: return res.data[0]
    u = {"id": uid, "wallet": 0, "tickets": 0, "display_name": "ተጫዋች", "step": ""}
    db.table("users").insert(u).execute()
    return u

def upd_u(uid, data): db.table("users").update(data).eq("id", str(uid)).execute()

# --- DESIGNER BOARD ---
def draw_board():
    s = get_s()
    b = s.get('board', {})
    p = s.get('prizes', [0,0,0])
    
    txt = f"🌟 **የፋሲል ዕጣ ልዩ የዕድል ሰሌዳ** 🌟\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{s['price']} ETB` | 🎫 **የተያዙ:** `{len(b)}/100` \n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # ሰሌዳውን በ 5x20 መልክ ዲዛይን ማድረግ
    grid = ""
    for i in range(1, 101):
        num = str(i)
        if num in b:
            grid += "🔴 " # የተያዘ ቁጥር
        else:
            grid += f"{i:02d} " # ክፍት ቁጥር
        if i % 10 == 0: grid += "\n"
    
    txt += grid
    txt += f"\n━━━━━━━━━━━━━━━━━━━━\n"
    txt += f"🏆 **የሽልማት ዝርዝር**\n"
    txt += f"🥇 1ኛ: `{p[0]} ETB` | 🥈 2ኛ: `{p[1]} ETB` | 🥉 3ኛ: `{p[2]} ETB` \n"
    txt += f"━━━━━━━━━━━━━━━━━━━━\n"
    txt += f"🕹 ለመሳተፍ @Fasil_assistant_bot"
    return txt

def push_board(reset=False):
    s = get_s()
    txt = draw_board()
    try:
        if reset:
            # የቆየውን ማጥፋት (ከተቻለ)
            if s.get('msg_id'):
                try: bot.delete_message(GROUP_ID, s['msg_id'])
                except: pass
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            s['msg_id'] = m.message_id
            save_s(s)
            bot.pin_chat_message(GROUP_ID, m.message_id)
        else:
            bot.edit_message_text(txt, GROUP_ID, s['msg_id'], parse_mode="Markdown")
    except Exception as e:
        # መልዕክቱ ካልተገኘ አዲስ ይላካል
        m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
        s['msg_id'] = m.message_id
        save_s(s)
        bot.pin_chat_message(GROUP_ID, m.message_id)

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid, s = str(c.from_user.id), get_s()
    u = get_u(c.from_user.id)
    
    # Admin Approval Logic
    if c.data.startswith("ok_"):
        _, t_uid, amt = c.data.split("_")
        tks = int(float(amt) // s['price'])
        upd_u(t_uid, {"tickets": tks, "step": "ASK_NAME"})
        bot.send_message(t_uid, "✅ ደረሰኝዎ ጸድቋል! እባክዎ ስምዎን (የሚመዘገበውን) ይጻፉ፦")
        bot.edit_message_text(f"✅ ደረሰኝ ተቀብለሃል (Amount: {amt})", ADMIN_ID, c.message.message_id)

    elif c.data.startswith("no_"):
        t_uid = c.data.split("_")[1]
        bot.send_message(t_uid, "❌ ይቅርታ የላኩት ደረሰኝ ውድቅ ተደርጓል። እባክዎ ትክክለኛ መሆኑን ያረጋግጡ።")
        bot.edit_message_text("❌ ደረሰኝ ውድቅ ተደርጓል", ADMIN_ID, c.message.message_id)

    # Number Selection Logic
    elif c.data.startswith("n_"):
        num = c.data.split("_")[1]
        if u['tickets'] > 0:
            if num not in s['board']:
                s['board'][num] = {"display_name": u['display_name'], "id": uid}
                save_s(s)
                upd_u(uid, {"tickets": u['tickets'] - 1})
                push_board(False) # ቦርዱን አዘምን
                bot.answer_callback_query(c.id, f"ቁጥር {num} ተይዟል!")
                # አዲስ ቁልፍ እንዲመጣ መልዕክቱን አዘምን
                if u['tickets'] - 1 > 0:
                    show_numbers(uid, u['tickets'] - 1)
                else:
                    bot.send_message(uid, "🎉 ሁሉንም እጣዎችዎን መርጠው ጨርሰዋል። መልካም ዕድል!")
            else:
                bot.answer_callback_query(c.id, "ይቅርታ፣ ይህ ቁጥር ተይዟል!")

    # Admin Panel Actions
    elif c.data == "set_p": 
        upd_u(uid, {"step": "SET_PRICE"})
        bot.send_message(uid, "💰 አዲሱን የመደብ ዋጋ በቁጥር ብቻ ያስገቡ (ለምሳሌ: 50):")
    elif c.data == "set_z": 
        upd_u(uid, {"step": "SET_PRIZES"})
        bot.send_message(uid, "🏆 ሽልማቶችን በኮማ በመለየት ያስገቡ (ለምሳሌ: 1000, 500, 250):")
    elif c.data == "reset": 
        s['board'] = {}
        save_s(s)
        push_board(True)
        bot.answer_callback_query(c.id, "ሰሌዳው ጸድቷል! አዲስ ቦርድ ተልኳል።")

def show_numbers(uid, tickets_left):
    s = get_s()
    kb = telebot.types.InlineKeyboardMarkup(row_width=5)
    btns = []
    for i in range(1, 101):
        if str(i) not in s['board']:
            btns.append(telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}"))
    kb.add(*btns)
    bot.send_message(uid, f"🎟 ቀሪ እጣ፦ {tickets_left}\nእባክዎ ቁጥር ይምረጡ፦", reply_markup=kb)

# --- PRIVATE MESSAGES ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private(m):
    uid, u, s = str(m.from_user.id), get_u(m.from_user.id), get_s()

    if m.text == "/start":
        msg = (f"👋 ሰላም {m.from_user.first_name}! እንኳን ወደ ፋሲል ዕጣ በሰላም መጡ።\n\n"
               f"📜 **የአጠቃቀም መመሪያ፦**\n1️⃣ መጀመሪያ ከታች ባሉት ሂሳቦች ክፍያ ይፈጽሙ\n2️⃣ የደረሰኝ SMS እዚህ 'Forward' ያድርጉ\n3️⃣ ሲጸድቅልዎ ስምዎን ያስገቡና ቁጥር ይምረጡ\n\n"
               f"💰 **መደብ (Price):** `{s['price']} ETB`\n"
               f"🏦 **CBE:** `1000584461757`\n📱 **Telebirr:** `0951381356`\n\n"
               f"ደረሰኝዎን እዚህ ይላኩ 👇")
        kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🕹 ቁጥር ምረጥ", "💰 Wallet")
        if int(uid) == ADMIN_ID: kb.add("🛠 Admin Panel")
        bot.send_message(uid, msg, reply_markup=kb, parse_mode="Markdown")

    elif u['step'] == "SET_PRICE":
        try:
            s['price'] = int(m.text)
            save_s(s); upd_u(uid, {"step": ""})
            bot.send_message(uid, f"✅ የመደብ ዋጋ ወደ {m.text} ETB ተቀይሯል!")
        except: bot.send_message(uid, "❌ እባክዎ ቁጥር ብቻ ያስገቡ።")
    
    elif u['step'] == "SET_PRIZES":
        try:
            s['prizes'] = [int(x.strip()) for x in m.text.split(',')]
            save_s(s); upd_u(uid, {"step": ""})
            bot.send_message(uid, "✅ ሽልማቶች ተቀምጠዋል።")
        except: bot.send_message(uid, "❌ ስህተት! አጻጻፉ እንደዚህ ይሁን (100,50,20)")

    elif u['step'] == "ASK_NAME":
        upd_u(uid, {"display_name": m.text, "step": ""})
        bot.send_message(uid, f"✅ ስም ተመዝግቧል: {m.text}")
        show_numbers(uid, u['tickets'])

    elif m.text == "🛠 Admin Panel" and int(uid) == ADMIN_ID:
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="set_p"))
        kb.add(telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="set_z"))
        kb.add(telebot.types.InlineKeyboardButton("♻️ Reset & New Board", callback_data="reset"))
        bot.send_message(uid, "🛠 **የአድሚን መቆጣጠሪያ ፓነል**", reply_markup=kb, parse_mode="Markdown")

    elif m.text == "🕹 ቁጥር ምረጥ":
        if u['tickets'] <= 0: 
            bot.send_message(uid, "❌ በአሁኑ ሰዓት ምንም እጣ የለዎትም! መጀመሪያ ደረሰኝ ይላኩ።")
        else:
            show_numbers(uid, u['tickets'])

    elif m.text == "💰 Wallet":
        bot.send_message(uid, f"📊 **የእርስዎ መረጃ:**\n🎟 ያልተጠቀሙበት እጣ: {u['tickets']}\n👤 ስም: {u['display_name']}")

    # --- SMS & Payment Logic ---
    elif re.search(r"(FT|DCA|[0-9]{10})", m.text):
        amt_match = re.search(r"(?i)(?:ብር|amount|ETB)\s*[:]*\s*(\d+(?:\.\d+)?)", m.text)
        if not amt_match: # ብሩን በቀጥታ ካልገኘ የመጀመሪያውን ቁጥር ይውሰድ
            amt_match = re.search(r"(\d+)", m.text)
        
        amt = int(float(amt_match.group(1))) if amt_match else 0
        
        if amt < s['price']:
            bot.reply_to(m, f"⚠️ **ይቅርታ!** የላኩት ብር ({amt} ETB) ከመደብ ዋጋ ({s['price']} ETB) ያነሰ በመሆኑ መቀበል አንችልም።")
        else:
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_{amt}"),
                   telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
            bot.send_message(ADMIN_ID, f"📩 **አዲስ ደረሰኝ ቀርቧል:**\n👤 ከ: {m.from_user.first_name}\n💰 መጠን: {amt} ETB\n\n`{m.text}`", reply_markup=kb)
            bot.send_message(uid, "📩 ደረሰኝዎ ለኦፕሬተር ደርሷል። ሲረጋገጥ መልዕክት ይደርስዎታል።")

# --- SERVER ---
@app.route('/')
def h(): return "Fasil Bingo PRO Online"

if __name__ == "__main__":
    bot.remove_webhook()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
