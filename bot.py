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

# --- 2. DYNAMIC SETTINGS ---
SET_PRICE = 30.0            
TIME_LIMIT_MINS = 15       
MY_NAME = "FASIL"          
MY_CBE_LAST = "84461757"   
MY_PHONE_LAST = "51381356"
RENDER_URL = "https://fasil-bingo-bot-fasil-assistant.onrender.com"

# --- 🚀 KEEP ALIVE (ቦቱ እንዳይተኛ) ---
def keep_awake():
    while True:
        try:
            requests.get(RENDER_URL)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💤 ቦቱ ንቁ ነው!")
        except:
            pass
        time.sleep(300)

# --- 🛡️ የደረሰኝ ፍተሻ SEQUENCE ---
def verify_payment_sequence(text):
    text = text.upper()
    now = datetime.now()
    
    # ደረጃ 1: ባንክ ቼክ
    is_cbe = any(k in text for k in ["CBE", "COMMERCIAL", MY_CBE_LAST])
    is_tele = any(k in text for k in ["TELEBIRR", MY_PHONE_LAST, "RECEIVED", "MOBILE"])
    
    if not is_cbe and not is_tele:
        return False, "❌ ስህተት (ደረጃ 1)፦ የላኩት መልዕክት የ CBE ወይም የ Telebirr ደረሰኝ አይደለም።", None

    # ደረጃ 2: ሰዓት ቼክ
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        msg_h, msg_m = int(time_match.group(1)), int(time_match.group(2))
        if "PM" in text and msg_h < 12: msg_h += 12
        msg_time = now.replace(hour=msg_h, minute=msg_m, second=0, microsecond=0)
        diff = abs((now - msg_time).total_seconds() / 60)
        if diff > TIME_LIMIT_MINS:
            return False, f"❌ ስህተት (ደረጃ 2)፦ ደረሰኙ ጊዜው አልፏል። ገደቡ {TIME_LIMIT_MINS} ደቂቃ ነው።", None
    else:
        return False, "❌ ስህተት (ደረጃ 2)፦ በደረሰኙ ላይ የክፍያ ሰዓት አልተገኘም።", None

    # ደረጃ 3: አካውንት ቼክ
    if is_cbe and MY_CBE_LAST not in text:
        return False, f"❌ ስህተት (ደረጃ 3)፦ ደረሰኙ ወደ ፋሲል CBE አካውንት ({MY_CBE_LAST}) አልተላከም።", None
    if is_tele and MY_PHONE_LAST not in text:
        return False, f"❌ ስህተት (ደረጃ 3)፦ ደረሰኙ ወደ ፋሲል ቴሌብር ስልክ ({MY_PHONE_LAST}) አልተላከም።", None

    # ደረጃ 4: ዋጋ ቼክ
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT|AMOUNT)[:\s]*([\d\.]+)', text)
    if amounts:
        found_amt = float(amounts[0])
        if found_amt < SET_PRICE:
            return False, f"❌ ስህተት (ደረጃ 4)፦ መከፈል ያለበት {SET_PRICE} ብር ነው።", None
    else:
        return False, "❌ ስህተት (ደረጃ 4)፦ በደረሰኙ ላይ የብር መጠን አልተገኘም።", None

    tid_match = re.search(r'(?:FT|ID|TXN|TRANS)[:\s]*([A-Z0-9]+)', text)
    tid = tid_match.group(1) if tid_match else "TID" + str(int(time.time()))
    return True, "✅ Success", tid

# --- 🏠 KEYBOARDS ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
    if user_id == ADMIN_ID:
        markup.add("⚙️ Admin Panel")
    return markup

# --- 🛰️ HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        f"ሰላም {message.from_user.first_name}! 🎰 እንኳን ወደ **Fasil Bingo Bot** በሰላም መጡ።\n\n"
        "🎯 **ለመመዝገብ የሚከተሉትን ይከተሉ፦**\n"
        "1️⃣ መጀመሪያ ክፍያዎን በ CBE ወይም Telebirr ይፈጽሙ።\n"
        "2️⃣ ከባንክ የደረሰዎትን **የ SMS መልዕክት** እዚህ Forward ያድርጉ።\n"
        "3️⃣ ከዚያም ስምዎን እና የሚፈልጉትን ቁጥር ያስገቡ።\n\n"
        "👇 አማራጮችን ለመጠቀም ከታች ያሉትን ቁልፎች ይጫኑ።"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(message.from_user.id), parse_mode="Markdown")

# --- ⚙️ ADMIN PANEL ---
@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📊 የዛሬ ሪፖርት", "🔄 ዙር ቀይር (Reset)", "🏠 ወደ ዋና ሜኑ")
    bot.send_message(ADMIN_ID, "እንኳን ደህና መጡ አድሚን ፋሲል! ምን ማድረግ ይፈልጋሉ?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and message.text == "📊 የዛሬ ሪፖርት")
def admin_report(message):
    try:
        res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", True).execute()
        booked = len(res.data)
        bot.send_message(ADMIN_ID, f"📊 **ሪፖርት**\n\n🎟 የተያዙ ቁጥሮች፦ {booked}\n💰 አጠቃላይ ብር፦ {booked * SET_PRICE} ብር", parse_mode="Markdown")
    except:
        bot.send_message(ADMIN_ID, "ሪፖርት ማምጣት አልተቻለም።")

@bot.message_handler(func=lambda message: message.text == "🏠 ወደ ዋና ሜኑ")
def back_home(message):
    bot.send_message(message.chat.id, "ወደ ዋና ሜኑ ተመልሰናል", reply_markup=main_menu(message.from_user.id))

# --- 🎰 LOGIC ---
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""
    
    # ደረሰኝ ፍተሻ
    bank_keys = ['cbe', 'telebirr', 'ብር', 'transferred', 'credited', 'sent', 'received', 'dash']
    if any(k in txt.lower() for k in bank_keys):
        bot.reply_to(message, "⏳ ደረሰኙን እያረጋገጥኩ ነው...")
        is_valid, reason, tid = verify_payment_sequence(txt)
        if not is_valid:
            bot.reply_to(message, reason)
            return
        
        pending_payments[u_id] = {"tid": tid, "step": "name"}
        bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! አሁን በቦርዱ ላይ እንዲሰፍር የሚፈልጉትን ስም ይላኩ።")
        return

    # የምዝገባ ሂደት
    if u_id in pending_payments:
        if pending_payments[u_id]["step"] == "name":
            pending_payments[u_id]["name"] = txt
            pending_payments[u_id]["step"] = "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን ከ 1-100 ክፍት ቁጥር ይላኩ።")
        elif pending_payments[u_id]["step"] == "num" and txt.isdigit():
            num = int(txt)
            if 1 <= num <= 100:
                name = pending_payments[u_id]["name"]
                tid = pending_payments[u_id]["tid"]
                try:
                    supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                    supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                    bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                    bot.send_message(GROUP_ID, f"🎰 **አዲስ ተመዝጋቢ!**\n👤 ስም፦ {name}\n🎟 ቁጥር፦ {num}")
                    del pending_payments[u_id]
                except:
                    bot.reply_to(message, "ምዝገባው አልተሳካም።")
            else:
                bot.reply_to(message, "እባክዎ ከ 1-100 ያለ ቁጥር ይላኩ።")
        return

    # ምላሽ ለሌላ ጽሁፍ
    if message.text == "📖 እንዴት መጫወት ይቻላል?":
        bot.reply_to(message, "1️⃣ ክፍያ ይፈጽሙ\n2️⃣ ደረሰኙን እዚህ Forward ያድርጉ\n3️⃣ ስምዎን ይላኩ\n4️⃣ ቁጥር ይምረጡ")
    elif message.text == "📊 ክፍት ቁጥሮችን እይ":
        res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).execute()
        nums = [str(r['slot_number']) for r in res.data]
        bot.reply_to(message, f"📊 ክፍት ቁጥሮች፦\n{', '.join(nums)}" if nums else "ሁሉም ተይዘዋል።")
    elif message.text == "💰 የጨዋታ ዋጋ":
        bot.reply_to(message, f"💰 ዋጋ፦ {SET_PRICE} ብር\n🏦 CBE: 1000584461757\n📱 Telebirr: 0951381356")

# --- 5. RUN SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "I am alive!"

if __name__ == "__main__":
    threading.Thread(target=keep_awake, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except:
            time.sleep(5)
