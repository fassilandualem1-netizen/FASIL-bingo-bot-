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
admin_states = {} # ለአድሚን ተግባራት መቆጣጠሪያ

# --- 2. DYNAMIC SETTINGS ---
SET_PRICE = 30.0            
TIME_LIMIT_MINS = 15       
MY_NAME = "FASIL"          
MY_CBE_LAST = "84461757"   
MY_PHONE_LAST = "51381356"
RENDER_URL = "https://fasil-bingo-bot-fasil-assistant.onrender.com"

# --- 🚀 KEEP ALIVE ---
def keep_awake():
    while True:
        try: requests.get(RENDER_URL)
        except: pass
        time.sleep(300)

# --- 🛡️ VERIFIER ---
def verify_payment_sequence(text):
    text = text.upper()
    now = datetime.now()
    is_cbe = any(k in text for k in ["CBE", "COMMERCIAL", MY_CBE_LAST])
    is_tele = any(k in text for k in ["TELEBIRR", MY_PHONE_LAST, "RECEIVED", "MOBILE"])
    if not is_cbe and not is_tele: return False, "❌ የ CBE ወይም የ Telebirr ደረሰኝ አይደለም።", None

    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        msg_h, msg_m = int(time_match.group(1)), int(time_match.group(2))
        if "PM" in text and msg_h < 12: msg_h += 12
        msg_time = now.replace(hour=msg_h, minute=msg_m, second=0, microsecond=0)
        if abs((now - msg_time).total_seconds() / 60) > TIME_LIMIT_MINS:
            return False, "❌ የደረሰኙ ሰዓት አልፏል።", None
    else: return False, "❌ ሰዓት አልተገኘም።", None

    if (is_cbe and MY_CBE_LAST not in text) or (is_tele and MY_PHONE_LAST not in text):
        return False, "❌ ወደ ፋሲል አካውንት አልተላከም።", None

    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT|AMOUNT)[:\s]*([\d\.]+)', text)
    if not amounts or float(amounts[0]) < SET_PRICE:
        return False, f"❌ ትክክለኛ የብር መጠን አልተገኘም። (ቢያንስ {SET_PRICE})", None

    tid = re.search(r'(?:FT|ID|TXN|TRANS)[:\s]*([A-Z0-9]+)', text)
    return True, "OK", tid.group(1) if tid else "TID"+str(int(time.time()))

# --- 🏠 KEYBOARDS ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
    if user_id == ADMIN_ID:
        markup.add("⚙️ Admin Panel")
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📊 የዛሬ ሪፖርት", "💰 ዋጋ ቀይር", "🔄 ዙር ቀይር (Reset)", "🏠 ወደ ዋና ሜኑ")
    return markup

# --- 🛰️ START HANDLER ---
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        f"ሰላም {message.from_user.first_name}! 🎰 እንኳን ወደ **Fasil Bingo Bot** መጡ።\n\n"
        "🎯 **ለመመዝገብ የሚከተሉትን ይከተሉ፦**\n"
        "1️⃣ መጀመሪያ ክፍያዎን ይፈጽሙ፦\n"
        "   🏦 **CBE:** `1000584461757`\n"
        "   📱 **Telebirr:** `0951381356`\n"
        f"   💵 **የአንድ ቁጥር ዋጋ:** `{SET_PRICE} ብር`\n\n"
        "2️⃣ የባንክ ደረሰኙን (SMS) እዚህ **Forward** ያድርጉ።\n"
        "3️⃣ ከዚያም ስምዎን እና የሚፈልጉትን ቁጥር ያስገቡ።"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(message.from_user.id), parse_mode="Markdown")

# --- ⚙️ ADMIN PANEL LOGIC ---
@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    bot.send_message(ADMIN_ID, "እንኳን ደህና መጡ አድሚን ፋሲል!", reply_markup=admin_menu())

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == "💰 ዋጋ ቀይር")
def ask_price(message):
    admin_states[ADMIN_ID] = "waiting_for_price"
    bot.send_message(ADMIN_ID, "እባክዎ አዲሱን የቢንጎ ዋጋ ያስገቡ (ለምሳሌ፦ 50)።")

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and admin_states.get(ADMIN_ID) == "waiting_for_price")
def set_new_price(message):
    global SET_PRICE
    try:
        new_price = float(message.text)
        SET_PRICE = new_price
        bot.send_message(ADMIN_ID, f"✅ የቢንጎ ዋጋ ወደ **{SET_PRICE} ብር** ተቀይሯል።", reply_markup=admin_menu(), parse_mode="Markdown")
        admin_states[ADMIN_ID] = None
    except:
        bot.send_message(ADMIN_ID, "❌ ስህተት! እባክዎ ቁጥር ብቻ ያስገቡ።")

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == "📊 የዛሬ ሪፖርት")
def admin_report(message):
    res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", True).execute()
    booked = len(res.data)
    bot.send_message(ADMIN_ID, f"📊 **ሪፖርት**\n\n🎟 የተያዙ ቁጥሮች፦ {booked}\n💰 አጠቃላይ ብር፦ {booked * SET_PRICE} ብር")

@bot.message_handler(func=lambda message: message.text == "🏠 ወደ ዋና ሜኑ")
def back_home(message):
    bot.send_message(message.chat.id, "ወደ ዋና ሜኑ ተመልሰናል", reply_markup=main_menu(message.from_user.id))

# --- 🎰 PROCESSES ---
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""
    
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'ብር', 'sent']):
        bot.reply_to(message, "⏳ ደረሰኙን እያረጋገጥኩ ነው...")
        is_valid, reason, tid = verify_payment_sequence(txt)
        if not is_valid:
            bot.reply_to(message, reason)
            return
        pending_payments[u_id] = {"tid": tid, "step": "name"}
        bot.reply_to(message, "✅ ተረጋግጧል! ስምዎን ይላኩ።")
        return

    if u_id in pending_payments:
        if pending_payments[u_id]["step"] == "name":
            pending_payments[u_id]["name"] = txt
            pending_payments[u_id]["step"] = "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን ቁጥር (1-100) ይላኩ።")
        elif pending_payments[u_id]["step"] == "num" and txt.isdigit():
            num = int(txt)
            if 1 <= num <= 100:
                name, tid = pending_payments[u_id]["name"], pending_payments[u_id]["tid"]
                supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 አዲስ ተመዝጋቢ፦ {name} (ቁጥር {num})")
                del pending_payments[u_id]
            else: bot.reply_to(message, "❌ ከ 1-100 ቁጥር ይላኩ።")
        return

app = Flask(__name__)
@app.route('/')
def home(): return "OK"

if __name__ == "__main__":
    threading.Thread(target=keep_awake, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    bot.infinity_polling()
