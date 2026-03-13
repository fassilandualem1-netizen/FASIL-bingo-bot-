import telebot
from supabase import create_client, Client
import re, time, os, threading
from datetime import datetime
from flask import Flask
from telebot import types

# --- 1. CONFIG ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 6445347265 
GROUP_ID = -1003881429974 
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}

# --- 2. SETTINGS (Flexible) ---
SET_PRICE = 30.0            
TIME_LIMIT_MINS = 15       
MY_NAME = "FASIL"          
MY_CBE_LAST = "84461757"   
MY_PHONE_LAST = "51381356"  

# --- 3. UTILITY FUNCTIONS ---

def verify_payment(text):
    """የደረሰኝ ጥብቅ ፍተሻ"""
    text = text.upper()
    now = datetime.now()

    # ሀ. የስም እና የአካውንት ፍተሻ
    has_my_info = (MY_NAME in text) or (MY_CBE_LAST in text) or (MY_PHONE_LAST in text)
    if not has_my_info:
        return False, "❌ ስህተት፦ ደረሰኙ ወደ እኔ (Fasil) የተላከ መሆኑን ማረጋገጥ አልተቻለም።", None

    # ለ. የብር መጠን ፍተሻ
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT|AMOUNT)[:\s]*([\d\.]+)', text)
    if amounts:
        found_amt = float(amounts[0])
        if found_amt < SET_PRICE:
            return False, f"❌ ስህተት፦ መከፈል ያለበት {SET_PRICE} ብር ነው። የላኩት ግን {found_amt} ብር ይላል።", None
    else:
        return False, "❌ ስህተት፦ በደረሰኙ ላይ የክፍያ መጠን አልተገኘም።", None

    # ሐ. የቀን ፍተሻ
    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', text)
    if date_match:
        msg_day, msg_month = int(date_match.group(1)), int(date_match.group(2))
        if msg_day != now.day or msg_month != now.month:
            return False, "❌ ስህተት፦ ደረሰኙ የዛሬ አይደለም።", None

    # መ. የሰዓት ፍተሻ
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        msg_h, msg_m = int(time_match.group(1)), int(time_match.group(2))
        msg_time = now.replace(hour=msg_h, minute=msg_m, second=0, microsecond=0)
        diff = abs((now - msg_time).total_seconds() / 60)
        if diff > TIME_LIMIT_MINS:
            return False, f"❌ ስህተት፦ ደረሰኙ ጊዜው አልፏል። (ገደቡ {TIME_LIMIT_MINS} ደቂቃ ነው)", None
    else:
        return False, "❌ ስህተት፦ በደረሰኙ ላይ የክፍያ ሰዓት አልተገኘም።", None

    # ሠ. TID ማውጣት
    tid_match = re.search(r'(?:FT|ID|TXN|TRANS)[:\s]*([A-Z0-9]+)', text)
    tid = tid_match.group(1) if tid_match else "TID" + str(int(time.time()))
    return True, "Success", tid

# --- 4. HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
    
    bot.send_message(
        message.chat.id, 
        f"ሰላም {message.from_user.first_name}! 🎰 እንኳን ወደ **Fasil Bingo Bot** መጡ።\n\nለመመዝገብ የባንክ መልዕክቱን (SMS) እዚህ Forward ያድርጉ።",
        reply_markup=markup, 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text in ["📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ"])
def menu_info(message):
    if message.text == "📖 እንዴት መጫወት ይቻላል?":
        msg = "1️⃣ ክፍያ ይፈጽሙ (CBE/Telebirr)\n2️⃣ ደረሰኙን እዚህ Forward ያድርጉ\n3️⃣ ስምዎን ይላኩ\n4️⃣ ቁጥር ይምረጡ"
    elif message.text == "📊 ክፍት ቁጥሮችን እይ":
        res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).execute()
        nums = [str(r['slot_number']) for r in res.data]
        msg = f"📊 ክፍት ቁጥሮች፦\n{', '.join(nums)}" if nums else "ሁሉም ቁጥሮች ተይዘዋል።"
    else:
        msg = f"💰 የአንድ ቁጥር ዋጋ፦ {SET_PRICE} ብር\n🏦 CBE: 1000584461757\n📱 Telebirr: 0951381356"
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""

    # 1. የባንክ መልዕክት ሲላክ (Smart Filter)
    bank_words = ['cbe', 'telebirr', 'ብር', 'transferred', 'credited', 'sent', 'received', 'dash']
    if any(k in txt.lower() for k in bank_words):
        bot.reply_to(message, "⏳ ደረሰኙን እያረጋገጥኩ ነው... እባክዎ ይታገሱ።")
        
        is_valid, reason, tid = verify_payment(txt)
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

    # 2. በምዝገባ ሂደት ውስጥ ከሆነ
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
                # ዳታቤዝ ምዝገባ
                supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 **አዲስ ተመዝጋቢ!**\n👤 ስም፦ {name}\n🎟 ቁጥር፦ {num}")
                del pending_payments[u_id]
            else:
                bot.reply_to(message, "❌ እባክዎ ከ 1-100 ያለ ቁጥር ይላኩ።")
        return

    # 3. የማይታወቅ መልዕክት ከሆነ (ለማንኛውም ወሬ)
    bot.reply_to(message, "⚠️ **ያልታወቀ መልዕክት!**\nለመመዝገብ የባንክ ደረሰኝዎን (SMS) እዚህ Forward ያድርጉ። ለሌላ መረጃ ከታች ያሉትን ቁልፎች ይጠቀሙ።")

# --- 5. SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Running"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    bot.infinity_polling()
