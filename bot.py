import telebot
from supabase import create_client, Client
import re, time, os, threading, random
from datetime import datetime
from flask import Flask

# --- CONFIG ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 6445347265 # ያንተ ID
GROUP_ID = -1003881429974 
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}

# --- ጥብቅ የፍተሻ ቅንጅቶች (Settings) ---
MY_CBE_LAST = "84461757"     # የአካውንትህ መጨረሻ 8 ቁጥሮች
MY_PHONE_LAST = "51381356"   # የስልክህ መጨረሻ 8 ቁጥሮች
PRICE = 30                  # መከፈል ያለበት ብር
TIME_LIMIT_MINS = 15        # የጊዜ ገደብ (ደቂቃ)

# --- 🛠 የፍተሻ ተግባራት (Utility Functions) ---

def is_time_valid(text):
    """ደረሰኙ ከ 15 ደቂቃ በላይ አለመቆየቱን ያረጋግጣል"""
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        msg_h, msg_m = int(time_match.group(1)), int(time_match.group(2))
        now = datetime.now()
        # የሰዓት ልዩነትን ማስላት
        msg_time = now.replace(hour=msg_h, minute=msg_m, second=0, microsecond=0)
        diff = abs((now - msg_time).total_seconds() / 60)
        return diff <= TIME_LIMIT_MINS
    return True # ሰዓት ከሌለ (ለጊዜው እንዲያልፍ)

def verify_payment(text):
    """Ultimate የጥበቃ ፍተሻ - ቴሌብር እና ሲቤ"""
    text = text.upper()
    
    # 1. የብር መጠን ፍተሻ (30 ብር እና ከዚያ በላይ መሆኑን)
    # የዝውውር ፊ (2-3 ብር) ቢኖር እንኳ 30 ብር መኖሩን ያረጋግጣል
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    valid_amount = False
    for a in amounts:
        if float(a) >= PRICE:
            valid_amount = True
            break
    if not valid_amount:
        return False, f"❌ ስህተት፦ መከፈል ያለበት {PRICE} ብር ነው።", None

    # 2. የጊዜ ገደብ ፍተሻ
    if not is_time_valid(text):
        return False, f"❌ ስህተት፦ ደረሰኙ ከ {TIME_LIMIT_MINS} ደቂቃ በላይ ቆይቷል።", None

    # 3. የ CBE (ንግድ ባንክ) ጥብቅ ፍተሻ
    if "COMMERCIAL" in text or "CBE" in text:
        tid_match = re.search(r'FT[A-Z0-9]+', text)
        if MY_CBE_LAST in text and tid_match:
            return True, "CBE", tid_match.group(0)
        else:
            return False, "❌ ስህተት፦ ደረሰኙ የእኔ አይደለም ወይም ትክክለኛ የ CBE ማጣቀሻ የለውም።", None

    # 4. የ Telebirr (ቴሌብር) ጥብቅ ፍተሻ
    elif "TELEBIRR" in text or "RECEIVED" in text:
        tid_match = re.search(r'(?:ID|TXN|TRANS)[:\s]*([0-9A-Z]+)', text)
        if MY_PHONE_LAST in text and tid_match:
            return True, "TELEBIRR", tid_match.group(1)
        else:
            return False, "❌ ስህተት፦ ደረሰኙ የእኔ ቴሌብር ላይ የገባ አይደለም።", None

    return False, "❌ ስህተት፦ ቦቱ የሚቀበለው የ CBE ወይም የ Telebirr ደረሰኝ ብቻ ነው።", None

# --- 🤖 አስተዳዳሪ ትዕዛዞች (Admin Commands) ---

@bot.message_handler(commands=['status'])
def status(message):
    if message.from_user.id == ADMIN_ID:
        res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", True).execute()
        booked = len(res.data)
        bot.reply_to(message, f"📊 የዙሩ ሁኔታ፦\n✅ የተያዙ፦ {booked}\n⬜️ ክፍት፦ {100 - booked}")

# --- 📩 ዋናው መልዕክት ተቀባይ ---

@bot.message_handler(func=lambda message: True)
def handle_msg(message):
    u_id = message.chat.id
    txt = message.text or ""

    # የባንክ መልዕክት መሆኑን መለየት
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'ብር', 'transferred', 'credited']):
        is_ok, status, tid = verify_payment(txt)
        
        if not is_ok:
            bot.reply_to(message, status)
            return

        # TID ቀደም ብሎ ጥቅም ላይ መዋሉን ቼክ ማድረግ
        check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
        if check.data:
            bot.reply_to(message, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል!")
            return

        pending_payments[u_id] = {"tid": tid, "step": "name"}
        bot.reply_to(message, f"✅ {status} ክፍያ ተረጋግጧል!\nአሁን በቦርዱ ላይ እንዲሰፍር የሚፈልጉትን ስም ይላኩ።")
        return

    # ስም መቀበል
    if u_id in pending_payments and pending_payments[u_id]["step"] == "name":
        pending_payments[u_id]["name"] = txt
        pending_payments[u_id]["step"] = "num"
        bot.reply_to(message, f"እሺ {txt}! አሁን ከ 1-100 የሚፈልጉትን ክፍት ቁጥር ይላኩ።")
        return

    # ቁጥር መቀበል
    if u_id in pending_payments and pending_payments[u_id]["step"] == "num" and txt.isdigit():
        num = int(txt)
        if 1 <= num <= 100:
            slot_check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            if slot_check.data and slot_check.data[0]['is_booked']:
                bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል፣ ሌላ ይምረጡ።")
            else:
                name = pending_payments[u_id]["name"]
                tid = pending_payments[u_id]["tid"]
                
                # ምዝገባ
                supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል። መልካም እድል!")
                bot.send_message(GROUP_ID, f"🎰 **አዲስ ተመዝጋቢ!**\n👤 ስም፦ {name}\n🎟 ቁጥር፦ {num}\n✅ በሰንጠረዡ ላይ ተሰይሟል።")
                del pending_payments[u_id]
        else:
            bot.reply_to(message, "❌ እባክዎ ከ 1-100 ያለ ቁጥር ይላኩ።")

# --- FLASK SERVER (For Render) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bingo Bot is Active!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
