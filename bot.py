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

# --- 💰 FLEXIBLE PRICE LOGIC ---
def get_current_price():
    try:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        if res.data:
            return float(res.data[0]['value'])
        return 30.0
    except:
        return 30.0

# --- 🛡️ VERIFIER ---
def verify_payment_sequence(text):
    text = text.upper()
    price = get_current_price()
    is_cbe = any(k in text for k in ["CBE", "COMMERCIAL", "84461757"])
    is_tele = any(k in text for k in ["TELEBIRR", "51381356", "RECEIVED"])
    
    if not is_cbe and not is_tele: return False, "❌ የባንክ ደረሰኝ አይደለም።", None
    
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT|AMOUNT)[:\s]*([\d\.]+)', text)
    if not amounts or float(amounts[0]) < price:
        return False, f"❌ መጠኑ ከወቅታዊው ዋጋ ({price} ብር) ያነሰ ነው።", None

    tid = re.search(r'(?:FT|ID|TXN|TRANS)[:\s]*([A-Z0-9]+)', text)
    return True, "OK", tid.group(1) if tid else "TID"+str(int(time.time()))

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
    welcome = (f"ሰላም {message.from_user.first_name}! 🎰 እንኳን ወደ **Fasil Bingo** መጡ።\n\n"
              f"🏦 **CBE:** `1000584461757`\n"
              f"📱 **Telebirr:** `0951381356`\n"
              f"💵 **የአሁኑ ዋጋ:** `{price} ብር`\n\n"
              "👉 ለመመዝገብ ደረሰኙን እዚህ Forward ያድርጉ።")
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(message.from_user.id), parse_mode="Markdown")

# --- ⚙️ ADMIN PANEL ---
@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📊 ሪፖርት", "💰 ዋጋ ቀይር", "🏠 ወደ ዋና ሜኑ")
    bot.send_message(ADMIN_ID, "የአድሚን መቆጣጠሪያ፦", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "💰 ዋጋ ቀይር" and message.from_user.id == ADMIN_ID)
def ask_price(message):
    admin_states[ADMIN_ID] = "waiting_for_price"
    bot.send_message(ADMIN_ID, "እባክዎ አዲሱን ዋጋ ያስገቡ (ለምሳሌ፦ 40)።")

@bot.message_handler(func=lambda message: admin_states.get(ADMIN_ID) == "waiting_for_price" and message.from_user.id == ADMIN_ID)
def update_price_db(message):
    try:
        new_val = float(message.text)
        supabase.table("settings").upsert({"key": "ticket_price", "value": str(new_val)}).execute()
        bot.send_message(ADMIN_ID, f"✅ ዋጋው ወደ {new_val} ብር ተቀይሯል።")
        admin_states[ADMIN_ID] = None
    except:
        bot.send_message(ADMIN_ID, "❌ ቁጥር ብቻ ያስገቡ።")

# --- 🎰 PROCESSES ---
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""
    
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'ብር']):
        is_valid, reason, tid = verify_payment_sequence(txt)
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
            bot.reply_to(message, f"እሺ {txt}! አሁን ክፍት ቁጥር ይላኩ።")
        elif pending_payments[u_id]["step"] == "num" and txt.isdigit():
            num = int(txt)
            name, tid = pending_payments[u_id]["name"], pending_payments[u_id]["tid"]
            try:
                supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 አዲስ ተመዝጋቢ፦ {name} (ቁጥር {num})")
                del pending_payments[u_id]
            except: bot.reply_to(message, "❌ ቁጥሩ ተይዟል ወይም ስህተት ተፈጥሯል።")
        return

    if message.text == "💰 የጨዋታ ዋጋ":
        bot.reply_to(message, f"💰 ወቅታዊ ዋጋ፦ {get_current_price()} ብር")

app = Flask(__name__)
@app.route('/')
def home(): return "OK"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    bot.infinity_polling()
