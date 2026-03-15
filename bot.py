import telebot
import re
import os
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
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- DB HELPERS ---
def get_s():
    res = db.table("game_state").select("value").eq("key", "current_game").execute()
    return res.data[0]['value'] if res.data else {"price": 20, "board": {}, "msg_id": None}

def save_s(s): db.table("game_state").update({"value": s}).eq("key", "current_game").execute()

def get_u(uid):
    uid = str(uid)
    res = db.table("users").select("*").eq("id", uid).execute()
    if res.data: return res.data[0]
    u = {"id": uid, "tickets": 0, "display_name": "Player", "step": ""}
    db.table("users").insert(u).execute()
    return u

def upd_u(uid, data): db.table("users").update(data).eq("id", str(uid)).execute()

# --- BOARD DESIGN ---
def draw_board():
    s = get_s()
    b = s.get('board', {})
    txt = f"🎰 **የፋሲል ዕጣ ልዩ ሰሌዳ** 🎰\n━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{s['price']} ETB`\n━━━━━━━━━━━━━\n"
    for i in range(1, 101):
        n = str(i)
        txt += f"{i:02d}.{b[n]['display_name'][:5]}🏆 " if n in b else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
    txt += "\n🕹 @Fasil_assistant_bot"
    return txt

def refresh_group():
    s = get_s()
    txt = draw_board()
    try:
        if s.get('msg_id'):
            bot.edit_message_text(txt, GROUP_ID, s['msg_id'], parse_mode="Markdown")
        else:
            m = bot.send_message(GROUP_ID, txt, parse_mode="Markdown")
            s['msg_id'] = m.message_id
            save_s(s)
            bot.pin_chat_message(GROUP_ID, m.message_id)
    except: pass

# --- CALLBACKS (Admin Action & Picking) ---
@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid, s, u = str(c.from_user.id), get_s(), get_u(c.from_user.id)
    
    # 1. አድሚን ሲያጸድቅ
    if c.data.startswith("ok_"):
        _, t_uid, amt = c.data.split("_")
        tks = int(float(amt) // s['price'])
        upd_u(t_uid, {"tickets": tks, "step": "ASK_NAME"})
        bot.send_message(t_uid, f"✅ ደረሰኝዎ ጸድቋል! {tks} እጣ ተሰጥቶዎታል።\nእባክዎ ስምዎን ይጻፉ፦")
        bot.delete_message(ADMIN_ID, c.message.message_id)

    # 2. አድሚን ውድቅ ሲያደርግ
    elif c.data.startswith("no_"):
        t_uid = c.data.split("_")[1]
        bot.send_message(t_uid, "❌ ይቅርታ የላኩት ደረሰኝ ስህተት ነው ወይም የቆየ ስለሆነ ውድቅ ተደርጓል።")
        bot.delete_message(ADMIN_ID, c.message.message_id)

    # 3. ቁጥር ሲመረጥ
    elif c.data.startswith("n_"):
        n = c.data.split("_")[1]
        if u['tickets'] > 0:
            s['board'][n] = {"display_name": u['display_name'], "id": uid}
            save_s(s); upd_u(uid, {"tickets": u['tickets'] - 1})
            refresh_group()
            bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተይዟል!")
        else:
            bot.answer_callback_query(c.id, "❌ እጣ የለዎትም!", show_alert=True)

# --- MESSAGES ---
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(m):
    uid, u, s = str(m.from_user.id), get_u(m.from_user.id), get_s()

    # ሀ. START
    if m.text == "/start":
        msg = (f"👋 ሰላም {m.from_user.first_name}!\n\n"
               f"💰 መደብ: `{s['price']} ETB`\n"
               f"🏦 CBE: `1000584461757`\n"
               f"📱 Telebirr: `0951381356`\n\n"
               f"እባክዎ የደረሰኝ SMS እዚህ ይላኩ 👇")
        kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🕹 ቁጥር ምረጥ", "🎫 የእኔ እጣ")
        bot.send_message(uid, msg, reply_markup=kb, parse_mode="Markdown")

    # ለ. ስም መቀበል (ከጸደቀ በኋላ ብቻ)
    elif u['step'] == "ASK_NAME":
        upd_u(uid, {"display_name": m.text, "step": ""})
        bot.send_message(uid, f"✅ {m.text} ተብለው ተመዝግበዋል። አሁን '🕹 ቁጥር ምረጥ' የሚለውን ይጫኑ።")

    # ሐ. ቁጥር መምረጥ
    elif m.text == "🕹 ቁጥር ምረጥ":
        if u['tickets'] <= 0:
            bot.send_message(uid, "❌ መጀመሪያ ደረሰኝ በመላክ እጣ ይግዙ።")
        else:
            kb = telebot.types.InlineKeyboardMarkup(row_width=5)
            btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") for i in range(1, 101) if str(i) not in s['board']]
            kb.add(*btns)
            bot.send_message(uid, "እባክዎ ቁጥር ይምረጡ፦", reply_markup=kb)

    # መ. እጣ ማየት
    elif m.text == "🎫 የእኔ እጣ":
        bot.send_message(uid, f"📊 ያለዎት ቀሪ እጣ: {u['tickets']}")

    # ሠ. ደረሰኝ መያዝ (SMS)
    elif re.search(r"(FT|DCA|[0-9]{10})", m.text):
        amt_match = re.search(r"(\d+)", m.text)
        amt = amt_match.group(1) if amt_match else "20"
        
        # ለአድሚን መላክ
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ", callback_data=f"ok_{uid}_{amt}"),
               telebot.types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"no_{uid}"))
        bot.send_message(ADMIN_ID, f"📩 **አዲስ ደረሰኝ መጥቷል**\n👤 ከ: {m.from_user.first_name}\n💰 መጠን: {amt} ETB\n📝 `{m.text[:100]}`", reply_markup=kb)
        bot.send_message(uid, "📩 ደረሰኝዎ ለአድሚን ተልኳል፣ እስኪጸድቅ ድረስ ትንሽ ይጠብቁ።")

# --- SERVER ---
@app.route('/')
def home(): return "OK"

if __name__ == "__main__":
    bot.remove_webhook()
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
