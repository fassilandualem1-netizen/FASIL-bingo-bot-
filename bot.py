import telebot
from supabase import create_client, Client
import re, time, os, threading, requests
from datetime import datetime
from flask import Flask
from telebot import types

# --- 1. CONFIGURATION ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZMi6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}
admin_states = {}

# --- 💰 DYNAMIC CONFIG ---
def get_config(key, default):
    try:
        res = supabase.table("settings").select("value").eq("key", key).execute()
        return res.data[0]['value'] if res.data else default
    except: return default

# --- 🛡️ STRICT VERIFIER (DATE, TIME, TID) ---
def verify_payment_strict(text):
    text = text.upper()
    now = datetime.now()
    today_date = now.strftime("%d/%m/%Y")
    
    # 1. Transaction ID Check
    tid_match = re.search(r'(?:ID|TXN|TRANS|FT|NUMBER IS)[:\s]*([A-Z0-9]{6,12})', text)
    if not tid_match: return False, "❌ የግብይት ቁጥር (ID) አልተገኘም።", None, None
    tid = tid_match.group(1)

    # 2. Date Check (የዛሬ መሆኑን ማረጋገጥ)
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    r_date = date_match.group(1) if date_match else today_date
    if r_date != today_date:
        return False, f"❌ ደረሰኙ የቆየ ነው ({r_date})። የዛሬ ደረሰኝ ብቻ ነው የሚቻለው።", None, None

    # 3. Double Payment Check (ዳታቤዝ)
    used = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
    if used.data: return False, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል።", None, None

    # 4. Price & Account Check
    price = float(get_config("ticket_price", "30"))
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    amt = float(amounts[0]) if amounts else 0
    if amt < price: return False, f"❌ መጠኑ ከ {price} ብር ያነሰ ነው።", None, None
    
    if "84461757" not in text and "51381356" not in text:
        return False, "❌ ደረሰኙ ወደ ፋሲል አካውንት አልተላከም።", None, None

    return True, amt, tid, r_date

# --- 🏠 KEYBOARDS ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
    if user_id == ADMIN_ID: markup.add("⚙️ Admin Panel")
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📊 ሪፖርት", "💰 ዋጋ ቀይር", "🔄 Reset", "🏠 ወደ ዋና ሜኑ")
    return markup

# --- 🛰️ HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    price = get_config("ticket_price", "30")
    welcome = (f"ሰላም {message.from_user.first_name}! 🎰 Fasil Bingo\n\n"
              f"🏦 **CBE:** `1000584461757`\n"
              f"📱 **Telebirr:** `0951381356`\n"
              f"💵 **ዋጋ:** `{price} ብር`\n\n"
              "👉 ለመመዝገብ ደረሰኙን (SMS) እዚህ **Forward** ያድርጉ።")
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(message.from_user.id), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    bot.send_message(ADMIN_ID, "የአድሚን መቆጣጠሪያ፦", reply_markup=admin_menu())

@bot.message_handler(func=lambda message: message.text == "💰 ዋጋ ቀይር" and message.from_user.id == ADMIN_ID)
def ask_price(message):
    admin_states[ADMIN_ID] = "waiting_for_price"
    bot.send_message(ADMIN_ID, "አዲሱን ዋጋ ያስገቡ (ለምሳሌ፦ 50)።")

@bot.message_handler(func=lambda message: admin_states.get(ADMIN_ID) == "waiting_for_price")
def set_price(message):
    try:
        val = float(message.text)
        supabase.table("settings").upsert({"key": "ticket_price", "value": str(val)}).execute()
        bot.send_message(ADMIN_ID, f"✅ ዋጋው ወደ {val} ብር ተቀይሯል።", reply_markup=admin_menu())
        admin_states[ADMIN_ID] = None
    except: bot.send_message(ADMIN_ID, "❌ ቁጥር ብቻ ያስገቡ።")

@bot.message_handler(func=lambda message: message.text == "🔄 Reset" and message.from_user.id == ADMIN_ID)
def reset_round(message):
    try:
        supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
        supabase.table("used_transactions").delete().neq("tid", "0").execute()
        bot.send_message(ADMIN_ID, "🔄 ሁሉም ቁጥሮች እና ደረሰኞች ጸድተዋል። አዲስ ዙር ተጀምሯል!")
    except: bot.send_message(ADMIN_ID, "❌ Reset አልተሳካም።")

# --- 🎰 PROCESS LOGIC ---
@bot.callback_query_handler(func=lambda call: call.data in ["reserve_next", "pick_another"])
def callback_query(call):
    u_id = call.message.chat.id
    if call.data == "reserve_next":
        p = pending_payments.get(u_id)
        if p:
            supabase.table("next_round_waiting").insert({
                "player_name": p["name"], "tid": p["tid"], "user_id": str(u_id), "amount": p["amt"]
            }).execute()
            bot.answer_callback_query(call.id, "✅ ለቀጣይ ዙር ተመዝግበሃል!")
            bot.edit_message_text("✅ መረጃዎ ለቀጣይ ዙር ተመዝግቧል። እናመሰግናለን!", u_id, call.message.message_id)
            del pending_payments[u_id]
    else:
        bot.edit_message_text("እሺ፣ ሌላ ክፍት ቁጥር ይላኩ።", u_id, call.message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""
    
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'ብር', 'transferred', 'dear']):
        is_valid, amt_or_reason, tid, r_date = verify_payment_strict(txt)
        if not is_valid:
            bot.reply_to(message, amt_or_reason)
            return
        pending_payments[u_id] = {"tid": tid, "amt": amt_or_reason, "date": r_date, "step": "name"}
        bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! አሁን ስምዎን ይላኩ።")
        return

    if u_id in pending_payments:
        p_data = pending_payments[u_id]
        if p_data["step"] == "name":
            p_data["name"] = txt
            p_data["step"] = "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን ቁጥር ይምረጡ።")
        elif p_data["step"] == "num" and txt.isdigit():
            num = int(txt)
            check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            if check.data and check.data[0]['is_booked']:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("አዎ፣ ለቀጣይ ይያዝ", callback_data="reserve_next"),
                           types.InlineKeyboardButton("አይ፣ ሌላ ልምረጥ", callback_data="pick_another"))
                bot.send_message(u_id, f"❌ ቁጥር {num} ተይዟል። ለቀጣይ ዙር ይያዝልህ?", reply_markup=markup)
            else:
                supabase.table("bingo_slots").update({"player_name": p_data["name"], "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": p_data["tid"], "user_id": str(u_id), "amount": p_data["amt"]}).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 አዲስ ተመዝጋቢ፦ {p_data['name']} (ቁጥር {num})")
                del pending_payments[u_id]
        return

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    bot.infinity_polling()
