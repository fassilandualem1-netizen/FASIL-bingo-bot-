import telebot
from supabase import create_client, Client
import re, time, os, threading, requests
from datetime import datetime
from flask import Flask
from telebot import types

# --- 1. CONFIGURATION ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 6445347265 
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

# --- 🚀 ራስን መቀስቀሻ (KEEP ALIVE) ---
def keep_awake():
    """በየ 5 ደቂቃው ሰርቨሩን በመቀስቀስ እንዳይተኛ ያደርጋል"""
    while True:
        try:
            requests.get(RENDER_URL) 
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💤 ቦቱ ንቁ ነው!")
        except Exception as e:
            print(f"Ping failed: {e}")
        time.sleep(300) # 5 ደቂቃ

# --- 🛡️ በደረጃ የሚፈትሽ (SEQUENCE VERIFIER) ---
def verify_payment_sequence(text):
    text = text.upper()
    now = datetime.now()
    
    # ደረጃ 1: ባንክ ቼክ
    is_cbe = any(k in text for k in ["CBE", "COMMERCIAL", MY_CBE_LAST])
    is_tele = any(k in text for k in ["TELEBIRR", MY_PHONE_LAST, "RECEIVED", "MOBILE"])
    
    if not is_cbe and not is_tele:
        return False, "❌ ስህተት (ደረጃ 1)፦ ደረሰኙ የ CBE ወይም የ Telebirr አይደለም።", None

    # ደረጃ 2: ቀን እና የ 15 ደቂቃ Rule ቼክ
    # ቀን ፍተሻ
    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', text)
    if date_match:
        msg_day, msg_month = int(date_match.group(1)), int(date_match.group(2))
        if msg_day != now.day or msg_month != now.month:
            return False, f"❌ ስህተት (ደረጃ 2)፦ ደረሰኙ የዛሬ አይደለም። የዛሬውን ይላኩ።", None
    else:
        return False, "❌ ስህተት (ደረጃ 2)፦ በደረሰኙ ላይ ቀን አልተገኘም።", None

    # ሰዓት ፍተሻ
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        msg_h, msg_m = int(time_match.group(1)), int(time_match.group(2))
        msg_time = now.replace(hour=msg_h, minute=msg_m, second=0, microsecond=0)
        diff = abs((now - msg_time).total_seconds() / 60)
        if diff > TIME_LIMIT_MINS:
            return False, f"❌ ስህተት (ደረጃ 2)፦ የደረሰኙ ሰዓት አልፏል። ከ {int(diff)} ደቂቃ በፊት ነው የተከፈለው።", None
    else:
        return False, "❌ ስህተት (ደረጃ 2)፦ በደረሰኙ ላይ ሰዓት አልተገኘም።", None

    # ደረጃ 3: አካውንት እና ስም ቼክ
    if is_cbe:
        if MY_CBE_LAST not in text or MY_NAME not in text:
            return False, f"❌ ስህተት (ደረጃ 3)፦ ደረሰኙ ወደ እኔ አካውንት ({MY_CBE_LAST}) አልተላከም።", None
    elif is_tele:
        if MY_PHONE_LAST not in text:
            return False, f"❌ ስህተት (ደረጃ 3)፦ ደረሰኙ ወደ እኔ ስልክ ({MY_PHONE_LAST}) አልተላከም።", None

    # ደረጃ 4: የዋጋ (SetPrice) ቼክ
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT|AMOUNT)[:\s]*([\d\.]+)', text)
    if amounts:
        found_amt = float(amounts[0])
        if found_amt < SET_PRICE:
            return False, f"❌ ስህተት (ደረጃ 4)፦ መከፈል ያለበት {SET_PRICE} ብር ነው። የእርስዎ ደረሰኝ ግን {found_amt} ብር ይላል።", None
    else:
        return False, "❌ ስህተት (ደረጃ 4)፦ በደረሰኙ ላይ የብር መጠን አልተገኘም።", None

    # ሁሉንም ካለፈ TID አውጥቶ መጨረስ
    tid_match = re.search(r'(?:FT|ID|TXN|TRANS)[:\s]*([A-Z0-9]+)', text)
    tid = tid_match.group(1) if tid_match else "TID" + str(int(time.time()))
    return True, "✅ ሁሉም መረጃዎች ትክክል ናቸው!", tid

# --- 4. MESSAGE HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
    bot.send_message(message.chat.id, f"ሰላም {message.from_user.first_name}! 🎰 እንኳን ወደ **Fasil Bingo Bot** በሰላም መጡ።\n\nለመመዝገብ የባንክ ደረሰኝዎን (SMS) እዚህ Forward ያድርጉ።", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ["📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ"])
def menu_info(message):
    if message.text == "📖 እንዴት መጫወት ይቻላል?":
        msg = "1️⃣ ክፍያ ይፈጽሙ (CBE/Telebirr)\n2️⃣ ደረሰኙን እዚህ Forward ያድርጉ\n3️⃣ ስምዎን ይላኩ\n4️⃣ ቁጥር ይምረጡ"
    elif message.text == "📊 ክፍት ቁጥሮችን እይ":
        res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).execute()
        nums = [str(r['slot_number']) for r in res.data]
        msg = f"📊 ክፍት ቁጥሮች፦\n{', '.join(nums)}" if nums else "ሁሉም ቁጥሮች ተይዘዋል።"
    else:
        msg = f"💰 የአንድ ቁጥር ዋጋ፦ **{SET_PRICE} ብር**\n🏦 CBE: 1000584461757\n📱 Telebirr: 0951381356"
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""

    # የባንክ መልዕክት መሆኑን መለየት
    bank_keywords = ['cbe', 'telebirr', 'ብር', 'transferred', 'credited', 'sent', 'received', 'dash']
    if any(k in txt.lower() for k in bank_keywords):
        bot.reply_to(message, "⏳ ደረሰኙን በደረጃ እያረጋገጥኩ ነው... እባክዎ ይታገሱ።")
        
        is_valid, reason, tid = verify_payment_sequence(txt)
        if not is_valid:
            bot.reply_to(message, reason)
            return

        try:
            check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
            if check.data:
                bot.reply_to(message, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል!")
                return
            
            pending_payments[u_id] = {"tid": tid, "step": "name"}
            bot.reply_to(message, f"✅ ክፍያ ተረጋግጧል! (TID: {tid})\nአሁን በቦርዱ ላይ እንዲሰፍር የሚፈልጉትን ስም ይላኩ።")
        except:
            bot.reply_to(message, "⚠️ ዳታቤዝ ላይ ችግር አለ።")
        return

    # የምዝገባ ሎጂክ (ስም እና ቁጥር መቀበያ)
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
                # ዳታቤዝ ማደስ
                supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 **አዲስ ተመዝጋቢ!**\n👤 ስም፦ {name}\n🎟 ቁጥር፦ {num}")
                del pending_payments[u_id]
            else:
                bot.reply_to(message, "❌ እባክዎ ከ 1-100 ያለ ቁጥር ይላኩ።")
        return

    # የማይታወቅ መልዕክት
    bot.reply_to(message, "⚠️ **ያልታወቀ መልዕክት!**\nለመመዝገብ የባንክ ደረሰኝዎን (SMS) እዚህ Forward ያድርጉ።")

# --- 5. SERVER RUN ---
app = Flask(__name__)
@app.route('/')
def home(): return "I am alive!"

if __name__ == "__main__":
    threading.Thread(target=keep_awake, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception:
            time.sleep(5)
