import telebot
from supabase import create_client, Client
import re, time, os, threading
from datetime import datetime
from flask import Flask

# --- 1. CONFIG ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
GROUP_ID = -1003881429974 
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7k)mEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}

# --- 2. SETTINGS (እዚህ ጋር መቀየር ትችላለህ) ---
SET_PRICE = 30.0            # መከፈል ያለበት ዋጋ
TIME_LIMIT_MINS = 15       # የደቂቃ ገደብ
MY_NAME = "FASIL"          # ደረሰኙ ላይ መኖር ያለበት ያንተ ስም
MY_CBE_LAST = "84461757"   # የአካውንትህ መጨረሻ
MY_TELE_LAST = "51381356"  # የስልክህ መጨረሻ

# --- 3. UTILITY FUNCTIONS ---

def verify_payment(text):
    text = text.upper()
    now = datetime.now()

    # ሀ. የስም እና የአካውንት ፍተሻ (ባንኩ ምንም ይሁን ምን ያንተ መሆኑን ማረጋገጫ)
    has_my_info = (MY_NAME in text) or (MY_CBE_LAST in text) or (MY_PHONE_LAST in text)
    if not has_my_info:
        return False, "❌ ስህተት፦ ደረሰኙ ወደ እኔ (Fasil) የተላከ መሆኑን ማረጋገጥ አልተቻለም። እባክዎ ትክክለኛውን ደረሰኝ ይላኩ።", None

    # ለ. የብር መጠን ፍተሻ (ከ SET_PRICE ጋር የተሳሰረ)
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT|AMOUNT)[:\s]*([\d\.]+)', text)
    found_amt = 0.0
    if amounts:
        found_amt = float(amounts[0]) # የመጀመሪያውን የብር መጠን ይወስዳል
        if found_amt < SET_PRICE:
            return False, f"❌ ስህተት፦ መከፈል ያለበት {SET_PRICE} ብር ነው። የላኩት ደረሰኝ ግን {found_amt} ብር ይላል።", None
    else:
        return False, "❌ ስህተት፦ በደረሰኙ ላይ የብር መጠን አልተገኘም።", None

    # ሐ. የቀን ፍተሻ (የዛሬ መሆኑን)
    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', text)
    if date_match:
        msg_day = int(date_match.group(1))
        msg_month = int(date_match.group(2))
        if msg_day != now.day or msg_month != now.month:
            return False, f"❌ ስህተት፦ ደረሰኙ የዛሬ አይደለም። የዛሬውን ደረሰኝ ይላኩ።", None
    else:
        return False, "❌ ስህተት፦ በደረሰኙ ላይ ቀን አልተገኘም።", None

    # መ. የሰዓት ፍተሻ (የ15 ደቂቃ ገደብ)
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        msg_h, msg_m = int(time_match.group(1)), int(time_match.group(2))
        # የኢትዮጵያ ሰዓት አቆጣጠርን ግምት ውስጥ ያስገባል (እንደ አስፈላጊነቱ ሰርቨሩ ላይ ማስተካከል ይቻላል)
        msg_time = now.replace(hour=msg_h, minute=msg_m, second=0, microsecond=0)
        diff = abs((now - msg_time).total_seconds() / 60)
        if diff > TIME_LIMIT_MINS:
            return False, f"❌ ስህተት፦ ደረሰኙ ጊዜው አልፏል። የተከፈለው ከ {int(diff)} ደቂቃ በፊት ነው። (ገደቡ {TIME_LIMIT_MINS} ደቂቃ ነው)", None
    else:
        return False, "❌ ስህተት፦ በደረሰኙ ላይ የክፍያ ሰዓት አልተገኘም።", None

    # ሠ. Transaction ID (TID) ማውጣት
    tid_match = re.search(r'(?:FT|ID|TXN|TRANS)[:\s]*([A-Z0-9]+)', text)
    if not tid_match:
        # ለሲቤ FT የሌለው ከሆነ ሌላ ቁጥር ይፈልጋል
        tid_match = re.search(r'(\d{10,})', text)
        
    if tid_match:
        return True, "Success", tid_match.group(1)
    
    return False, "❌ ስህተት፦ ትክክለኛ የማጣቀሻ ቁጥር (TID) አልተገኘም።", None

# --- 4. HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, f"ሰላም! 🎰 እንኳን መጡ።\n💰 ዋጋ፦ {SET_PRICE} ብር\n⏱ ገደብ፦ {TIME_LIMIT_MINS} ደቂቃ\n\nለመመዝገብ የባንክ መልዕክቱን (SMS) Forward ያድርጉ።")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""

    # የባንክ መልዕክት መሆኑን በቃላት መለየት
    bank_words = ['cbe', 'telebirr', 'transferred', 'credited', 'received', 'sent', 'ብር', 'account']
    if any(k in txt.lower() for k in bank_words):
        is_valid, reason, tid = verify_payment(txt)
        
        if not is_valid:
            bot.reply_to(message, reason) # ምክንያቱን በዝርዝር ይናገራል
            return

        # TID በዳታቤዝ ማረጋገጥ
        try:
            check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
            if check.data:
                bot.reply_to(message, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል!")
                return
            
            pending_payments[u_id] = {"tid": tid, "step": "name"}
            bot.reply_to(message, f"✅ ክፍያ ተረጋግጧል! (TID: {tid})\nአሁን በቦርዱ ላይ እንዲሰፍር የሚፈልጉትን ስም ይላኩ።")
        except:
            bot.reply_to(message, "⚠️ የዳታቤዝ ግንኙነት ችግር ተፈጥሯል።")
        return

    # የስም እና የቁጥር መቀበያ ክፍሎች (ባለፈው የሰጠሁህ ይቀጥላሉ...)
    if u_id in pending_payments:
        if pending_payments[u_id]["step"] == "name":
            pending_payments[u_id]["name"] = txt
            pending_payments[u_id]["step"] = "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን ከ 1-100 ክፍት ቁጥር ይላኩ።")
        elif pending_payments[u_id]["step"] == "num" and txt.isdigit():
            # (የምዝገባ ሎጂክ እዚህ ይገባል...)
            pass

# --- 5. SERVER ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Running"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    bot.infinity_polling()
