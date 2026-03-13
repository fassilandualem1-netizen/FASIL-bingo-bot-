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

# --- 💰 DYNAMIC PRICE ---
def get_current_price():
    try:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        return float(res.data[0]['value']) if res.data else 30.0
    except: return 30.0

# --- 🛡️ IMPROVED VERIFIER (DATE & TIME) ---
def verify_payment_strict(text):
    text = text.upper()
    now = datetime.now()
    today_date = now.strftime("%d/%m/%Y")
    
    # 1. የግብይት ቁጥር (TID)
    tid_match = re.search(r'(?:ID|TXN|TRANS|FT)[:\s]*([A-Z0-9]{6,12})', text)
    if not tid_match: return False, "❌ የግብይት ቁጥር (ID) አልተገኘም።", None, None, None
    tid = tid_match.group(1)

    # 2. ቀን እና ሰዓት ማውጣት
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    time_match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)?)', text)
    
    r_date = date_match.group(1) if date_match else today_date
    r_time = time_match.group(1) if time_match else now.strftime("%H:%M")

    # 3. የቆየ ደረሰኝ መፈተሻ (የዛሬ ብቻ)
    if r_date != today_date:
        return False, f"❌ ደረሰኙ የቆየ ነው ({r_date})። የዛሬ ደረሰኝ ብቻ ነው የሚቻለው።", None, None, None

    # 4. ዋጋ መፈተሻ
    price = get_current_price()
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    amt = float(amounts[0]) if amounts else 0
    if amt < price:
        return False, f"❌ መጠኑ ከ {price} ብር ያነሰ ነው።", None, None, None

    # 5. ዳታቤዝ ላይ መደገሙን ቼክ ማድረግ
    used = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
    if used.data:
        return False, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል።", None, None, None

    return True, amt, tid, r_date, r_time

# --- 🏠 KEYBOARDS ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
    if user_id == ADMIN_ID: markup.add("⚙️ Admin Panel")
    return markup

# --- 🛰️ HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    price = get_current_price()
    welcome = (f"ሰላም {message.from_user.first_name}! 🎰 Fasil Bingo\n\n"
              f"🏦 **CBE:** `1000584461757`\n"
              f"📱 **Telebirr:** `0951381356`\n"
              f"💵 **የአሁኑ ዋጋ:** `{price} ብር`\n\n"
              "👉 ለመመዝገብ ደረሰኙን (SMS) እዚህ **Forward** ያድርጉ።")
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(message.from_user.id), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📊 ሪፖርት", "💰 ዋጋ ቀይር", "🔄 Reset", "🏠 ወደ ዋና ሜኑ")
    bot.send_message(ADMIN_ID, "የአድሚን መቆጣጠሪያ፦", reply_markup=markup)

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

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""
    
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'ብር', 'transferred', 'dear']):
        is_valid, amt_or_reason, tid, r_date, r_time = verify_payment_strict(txt)
        if not is_valid:
            bot.reply_to(message, amt_or_reason)
            return
        
        pending_payments[u_id] = {"tid": tid, "amt": amt_or_reason, "date": r_date, "time": r_time, "step": "name"}
        bot.reply_to(message, f"✅ ክፍያ ተረጋግጧል! (ሰዓት፦ {r_time})\nአሁን ስምዎን ይላኩ።")
        return

    if u_id in pending_payments:
        p_data = pending_payments[u_id]
        if p_data["step"] == "name":
            p_data["name"] = txt
            p_data["step"] = "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን ቁጥር ይምረጡ።")
        elif p_data["step"] == "num" and txt.isdigit():
            num = int(txt)
            # ቁጥሩን መመዝገብ እና ደረሰኙን ሰዓት ጨምሮ ሴቭ ማድረግ
            try:
                supabase.table("bingo_slots").update({"player_name": p_data["name"], "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({
                    "tid": p_data["tid"], 
                    "user_id": str(u_id), 
                    "amount": p_data["amt"],
                    "receipt_date": p_data["date"],
                    "receipt_time": p_data["time"]
                }).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 አዲስ ተመዝጋቢ፦ {p_data['name']} (ቁጥር {num})")
                del pending_payments[u_id]
            except: bot.reply_to(message, "❌ ስህተት፦ ቁጥሩ ተይዞ ሊሆን ይችላል።")
        return

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    bot.infinity_polling()
