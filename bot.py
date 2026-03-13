import telebot
from supabase import create_client, Client
import re, time, os, threading, requests
from datetime import datetime
from flask import Flask
from telebot import types

# --- 1. CONFIGURATION ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
# ያንተ ትክክለኛ ID
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

# --- 🚀 ራስን መቀስቀሻ (Keep Awake) ---
def keep_awake():
    while True:
        try:
            requests.get(RENDER_URL) 
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💤 ቦቱ ንቁ ነው!")
        except Exception as e:
            print(f"Ping Error: {e}")
        time.sleep(300) # 5 ደቂቃ

# --- 🛡️ የደረሰኝ ፍተሻ Sequence ---
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
        return False, "❌ ስህተት (ደረጃ 2)፦ በደረሰኙ ላይ ሰዓት አልተገኘም።", None

    # ደረጃ 3: አካውንት ቼክ
    if is_cbe and MY_CBE_LAST not in text:
        return False, f"❌ ስህተት (ደረጃ 3)፦ ደረሰኙ ወደ ፋሲል አካውንት ({MY_CBE_LAST}) አልተላከም።", None
    if is_tele and MY_PHONE_LAST not in text:
        return False, f"❌ ስህተት (ደረጃ 3)፦ ደረሰኙ ወደ ፋሲል ስልክ ({MY_PHONE_LAST}) አልተላከም።", None

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

# --- 🛠 ADMIN COMMANDS ---
@bot.message_handler(commands=['admin_stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", True).execute()
        total_booked = len(res.data)
        bot.send_message(ADMIN_ID, f"📊 **ሪፖርት**\n\n🎟 የተያዙ ቁጥሮች፦ {total_booked}\n💰 አጠቃላይ ብር፦ {total_booked * SET_PRICE} ብር")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"Error: {e}")

@bot.message_handler(commands=['set_price'])
def change_price(message):
    global SET_PRICE
    if message.from_user.id != ADMIN_ID: return
    try:
        SET_PRICE = float(message.text.split()[1])
        bot.send_message(ADMIN_ID, f"✅ ዋጋ ወደ {SET_PRICE} ብር ተቀይሯል።")
    except:
        bot.send_message(ADMIN_ID, "አጠቃቀም፦ /set_price 50")

# --- 4. MAIN HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    try:
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
        bot.send_message(message.chat.id, f"ሰላም {message.from_user.first_name}! 🎰 እንኳን ወደ Fasil Bingo Bot በሰላም መጡ።", reply_markup=markup)
    except Exception as e:
        print(f"Start Error: {e}")

@bot.message_handler(func=lambda message: message.text in ["📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ"])
def menu_info(message):
    if message.text == "📖 እንዴት መጫወት ይቻላል?":
        msg = "1️⃣ ክፍያ ይፈጽሙ\n2️⃣ ደረሰኙን እዚህ Forward ያድርጉ\n3️⃣ ስምዎን ይላኩ\n4️⃣ ቁጥር ይምረጡ"
    elif message.text == "📊 ክፍት ቁጥሮችን እይ":
        try:
            res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).execute()
            nums = [str(r['slot_number']) for r in res.data]
            msg = f"📊 ክፍት ቁጥሮች፦\n{', '.join(nums)}" if nums else "ሁሉም ተይዘዋል።"
        except: msg = "ዳታቤዝ ማግኘት አልተቻለም።"
    else:
        msg = f"💰 ዋጋ፦ {SET_PRICE} ብር\n🏦 CBE: 1000584461757\n📱 Telebirr: 0951381356"
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""
    
    bank_keys = ['cbe', 'telebirr', 'ብር', 'transferred', 'credited', 'sent', 'received', 'dash']
    if any(k in txt.lower() for k in bank_keys):
        bot.reply_to(message, "⏳ እያረጋገጥኩ ነው...")
        is_valid, reason, tid = verify_payment_sequence(txt)
        if not is_valid:
            bot.reply_to(message, reason)
            return
        
        try:
            check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
            if check.data:
                bot.reply_to(message, "❌ ይህ ደረሰኝ ጥቅም ላይ ውሏል!")
                return
            
            pending_payments[u_id] = {"tid": tid, "step": "name"}
            bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! አሁን ስምዎን ይላኩ።")
        except:
            bot.reply_to(message, "⚠️ ዳታቤዝ ችግር!")
        return

    if u_id in pending_payments:
        if pending_payments[u_id]["step"] == "name":
            pending_payments[u_id]["name"] = txt
            pending_payments[u_id]["step"] = "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን ቁጥር (1-100) ይላኩ።")
        elif pending_payments[u_id]["step"] == "num" and txt.isdigit():
            try:
                num = int(txt)
                name = pending_payments[u_id]["name"]
                tid = pending_payments[u_id]["tid"]
                supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.send_message(GROUP_ID, f"🎰 **አዲስ ተመዝጋቢ!**\n👤 ስም፦ {name}\n🎟 ቁጥር፦ {num}")
                del pending_payments[u_id]
            except Exception as e:
                bot.reply_to(message, f"ምዝገባው አልተሳካም፦ {e}")
        return

# --- 5. SERVER RUN ---
app = Flask(__name__)
@app.route('/')
def home(): return "I am alive!"

if __name__ == "__main__":
    threading.Thread(target=keep_awake, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)
