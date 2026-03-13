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
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}
admin_states = {}

# --- 2. DYNAMIC SETTINGS ---
MY_CBE = "84461757"
MY_TELE = "51381356"

def get_config(key, default):
    try:
        res = supabase.table("settings").select("value").eq("key", key).execute()
        return res.data[0]['value'] if res.data else default
    except: return default

# --- 🛡️ ጥብቅ የደረሰኝ ፍተሻ (STRICT VERIFIER) ---
def verify_payment_strict(text):
    text = text.upper()
    now = datetime.now()
    today_str = now.strftime("%d/%m/%Y") # ዛሬን መፈተሻ
    
    # 1. የግብይት ቁጥር መፈለግ (TID)
    tid_match = re.search(r'(?:ID|TXN|TRANS|FT)[:\s]*([A-Z0-9]{6,12})', text)
    if not tid_match: return False, "❌ ስህተት፦ የግብይት ቁጥር (Transaction ID) አልተገኘም።", None
    tid = tid_match.group(1)

    # 2. የቆየ ደረሰኝ መከላከያ (Date Check)
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    if date_match and date_match.group(1) != today_str:
        return False, f"❌ ስህተት፦ ደረሰኙ የቆየ ነው። የዛሬ ደረሰኝ ብቻ ነው የሚቻለው።", None

    # 3. የቲኬት ዋጋ መፈተሽ
    price = float(get_config("ticket_price", "30"))
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    if not amounts or float(amounts[0]) < price:
        return False, f"❌ ስህተት፦ የተከፈለው መጠን ከ {price} ብር ያነሰ ነው።", None

    # 4. የአካውንት ባለቤት መፈተሽ
    is_to_me = (MY_CBE in text) or (MY_TELE in text)
    if not is_to_me:
        return False, "❌ ስህተት፦ ደረሰኙ ወደ ፋሲል አካውንት አልተላከም።", None

    # 5. ደረሰኙ ከዚህ በፊት ጥቅም ላይ መዋሉን መፈተሽ
    used = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
    if used.data:
        return False, "❌ ስህተት፦ ይህ ደረሰኝ ከዚህ በፊት ጥቅም ላይ ውሏል።", None

    return True, "✅ Success", tid

# --- 🏠 KEYBOARDS ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
    if user_id == ADMIN_ID: markup.add("⚙️ Admin Panel")
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📊 ሪፖርት", "💰 ዋጋ ቀይር", "🔄 ዙር ቀይር (Reset)", "🏠 ወደ ዋና ሜኑ")
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

# --- 💰 ዋጋ መቀየሪያ (FIXED) ---
@bot.message_handler(func=lambda message: message.text == "💰 ዋጋ ቀይር" and message.from_user.id == ADMIN_ID)
def ask_price(message):
    admin_states[ADMIN_ID] = "waiting_for_price"
    bot.send_message(ADMIN_ID, "አዲሱን ዋጋ ያስገቡ (ለምሳሌ፦ 50)።")

@bot.message_handler(func=lambda message: admin_states.get(ADMIN_ID) == "waiting_for_price")
def set_price(message):
    if message.from_user.id == ADMIN_ID:
        try:
            val = float(message.text)
            supabase.table("settings").upsert({"key": "ticket_price", "value": str(val)}).execute()
            bot.send_message(ADMIN_ID, f"✅ ዋጋው ወደ {val} ብር ተቀይሯል።")
            admin_states[ADMIN_ID] = None
        except: bot.send_message(ADMIN_ID, "❌ ቁጥር ብቻ ያስገቡ።")

# --- 🔄 RESET LOGIC (FIXED) ---
@bot.message_handler(func=lambda message: message.text == "🔄 ዙር ቀይር (Reset)" and message.from_user.id == ADMIN_ID)
def reset_round(message):
    try:
        supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
        supabase.table("used_transactions").delete().neq("tid", "0").execute()
        bot.send_message(ADMIN_ID, "🔄 ሁሉም ቁጥሮች እና ደረሰኞች ጸድተዋል። አዲስ ዙር ተጀምሯል!")
    except: bot.send_message(ADMIN_ID, "❌ Reset ማድረግ አልተሳካም።")

# --- 🎰 ደረሰኝ መቀበያ ---
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""
    
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'ብር', 'transferred']):
        bot.reply_to(message, "⏳ ደረሰኙን በጥብቅ እያረጋገጥኩ ነው...")
        is_valid, reason, tid = verify_payment_strict(txt)
        if not is_valid:
            bot.reply_to(message, reason)
            return
        pending_payments[u_id] = {"tid": tid, "step": "name"}
        bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! ስምዎን ይላኩ።")
        return

    if u_id in pending_payments:
        if pending_payments[u_id]["step"] == "name":
            pending_payments[u_id]["name"] = txt
            pending_payments[u_id]["step"] = "num"
            bot.reply_to(message, "እሺ! አሁን ክፍት ቁጥር ይላኩ።")
        elif pending_payments[u_id]["step"] == "num" and txt.isdigit():
            num = int(txt)
            try:
                # ቁጥሩ መያዙን ቼክ ማድረግ
                check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check.data and check.data[0]['is_booked']:
                    bot.reply_to(message, "❌ ቁጥሩ ተይዟል! እባክዎ ሌላ ይምረጡ።")
                    return
                
                name, tid = pending_payments[u_id]["name"], pending_payments[u_id]["tid"]
                supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 አዲስ ተመዝጋቢ፦ {name} (ቁጥር {num})")
                del pending_payments[u_id]
            except: bot.reply_to(message, "❌ ስህተት ተፈጥሯል።")
        return

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    bot.infinity_polling()
