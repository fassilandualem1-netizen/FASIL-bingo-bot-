import telebot
from supabase import create_client, Client
import re, time, os, threading, schedule
from flask import Flask

# --- 1. Flask ለ Render (ሰርቨሩ እንዳይጠፋ) ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "Bot is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. CONFIGURATION ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
GROUP_ID = -1003881429974
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)

# የአንተ መረጃዎች (ስምህ በማንኛውም አጻጻፍ ቢመጣ እንዲረዳው)
MY_NAMES = ["fasil", "fassil", "andualem", "fassil andualem", "fasil andualem"]
MY_CBE = "1000584461757"
MY_TELEBIRR = "0951381356"

pending_payments = {}

# --- 3. አጋዥ ተግባራት (Validation) ---
def is_valid_bank_sms(text):
    text = text.lower()
    # የካርድ መሙያ መልዕክቶችን ውድቅ ማድረግ
    if any(k in text for k in ['recharge', 'airtime', 'ካርድ', 'መሙያ']): return False
    
    # የባንክ ቃላቶች መኖራቸውን ማረጋገጥ
    bank_keywords = ['cbe', 'telebirr', 'birr', 'ብር', 'transferred', 'received', 'sent']
    has_bank = any(k in text for k in bank_keywords)
    
    # ያንተ መረጃ መኖሩን ማረጋገጥ
    has_my_info = any(n in text for n in MY_NAMES) or MY_CBE in text or MY_TELEBIRR in text
    
    return has_bank and has_my_info

def send_auto_announcement():
    try:
        res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).execute()
        count = len(res.data)
        if count > 0:
            bot.send_message(GROUP_ID, f"📢 **የቢንጎ ወቅታዊ መረጃ**\n\n🎟 የቀሩ ክፍት ቦታዎች፦ {count}\n✅ አሁኑኑ ተመዝግበው እድልዎን ይሞክሩ!\n\nለመመዝገብ @Fasil_Bingo_Bot ን ይጠቀሙ።", parse_mode="Markdown")
    except: pass

# --- 4. የቦት ትዕዛዞች (Commands) ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        f"ሰላም {message.from_user.first_name}! የ FASIL VIP ቢንጎ ቦት ነው። 🎰\n\n"
        "📖 መመሪያ ለማየት: /howtoplay\n"
        "🎟 የቢንጎ ቦርድ ለማየት: /viewslot\n"
        "🎫 የገዙትን ቁጥር ለማየት: /my_tickets\n"
        "💰 ለመመዝገብ: የክፍያ መልዕክቱን (SMS) Forward ያድርጉ።"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['howtoplay'])
def how_to_play(message):
    text = (
        "📖 **እንዴት መጫወት ይቻላል?**\n\n"
        "1️⃣ በ CBE (1000584461757) ወይም በ Telebirr (0951381356) ክፍያ ይፈጽሙ።\n"
        "2️⃣ የደረሰኝ መልዕክቱን (SMS) ለዚህ ቦት Forward ያድርጉ።\n"
        "3️⃣ ቦቱ ክፍያውን ሲያረጋግጥ ቁጥር እንዲመርጡ ይጠይቅዎታል።\n"
        "4️⃣ ከ 1-100 ያለ ቁጥር ይላኩ።\n"
        "5️⃣ ምዝገባዎ ሲጠናቀቅ በግሩፑ ላይ ይፋ ይደረጋል!"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['viewslot'])
def view_slots(message):
    try:
        res = supabase.table("bingo_slots").select("slot_number", "is_booked").order("slot_number").execute()
        board = "🎰 **የቢንጎ ቦርድ (1-100)**\n\n"
        row_text = ""
        for i, row in enumerate(res.data):
            status = "❌" if row['is_booked'] else f"{row['slot_number']:02d}"
            row_text += f"| {status} "
            if (i + 1) % 5 == 0:
                board += row_text + "|\n"
                row_text = ""
        bot.reply_to(message, board, parse_mode="Markdown")
    except: bot.reply_to(message, "⚠️ ቦርዱን ማምጣት አልተቻለም።")

@bot.message_handler(commands=['my_tickets'])
def my_tickets(message):
    try:
        user_name = message.from_user.first_name
        res = supabase.table("bingo_slots").select("slot_number").eq("player_name", user_name).eq("is_booked", True).execute()
        tickets = [str(row['slot_number']) for row in res.data]
        if tickets:
            bot.reply_to(message, f"🎫 **{user_name}** የገዙት ቁጥሮች፦\n\n" + ", ".join(tickets))
        else:
            bot.reply_to(message, "⚠️ እስካሁን ምንም ቁጥር አልገዙም።")
    except: bot.reply_to(message, "⚠️ መረጃውን ማግኘት አልተቻለም።")

# --- 5. ዋናው መልዕክት ተቀባይ ---

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = message.chat.id
    text = message.text or ""

    # ሀ. የባንክ መልዕክት ከሆነ
    if is_valid_bank_sms(text):
        bot.reply_to(message, "⏳ መልዕክቱ ደርሶኛል፣ እያረጋገጥኩ ነው... እባክዎ ጥቂት ሰከንዶችን ይጠብቁ።")
        
        # የ TID ቁጥር ፍለጋ (CBE እና Telebirrን ጨምሮ)
        tid_match = re.search(r'(?i)(?:txn|id|ማጣቀሻ|Ref|Reference|ቁጥር|TxnID)\s*(?:no\.|:)?\s*([a-z0-9]+)', text)
        
        if tid_match:
            tid = tid_match.group(1).upper()
            try:
                # ተደጋጋሚ ቼክ
                check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
                if check.data:
                    bot.reply_to(message, "❌ ይቅርታ፣ ይህ ማጣቀሻ ቁጥር (TID) ቀደም ብሎ ጥቅም ላይ ውሏል!")
                    return
                
                # ለመመዝገቢያ ዝግጁ ማድረግ
                pending_payments[user_id] = {"name": message.from_user.first_name, "tid": tid}
                bot.reply_to(message, "✅ ክፍያዎ ተረጋግጧል! አሁን ከ 1 እስከ 100 ባለው ውስጥ የሚፈልጉትን የቢንጎ ቁጥር ይላኩ።")
            except:
                bot.reply_to(message, "⚠️ የዳታቤዝ ስህተት አጋጥሟል።")
        else:
            bot.reply_to(message, "❌ ማጣቀሻ ቁጥር (Transaction ID) ማግኘት አልቻልኩም። እባክዎ ሙሉውን የባንክ መልዕክት Forward ማድረጉን ያረጋግጡ።")

    # ለ. ቁጥር ምርጫ ከሆነ
    elif user_id in pending_payments and text.isdigit():
        num = int(text)
        if 1 <= num <= 100:
            try:
                check_slot = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check_slot.data and check_slot.data[0]['is_booked']:
                    bot.reply_to(message, f"❌ ቁጥር {num} ቀደም ብሎ ተይዟል። እባክዎ ሌላ ቁጥር ይምረጡ።")
                else:
                    # በዳታቤዝ መመዝገብ
                    supabase.table("bingo_slots").update({"player_name": pending_payments[user_id]["name"], "is_booked": True}).eq("slot_number", num).execute()
                    supabase.table("used_transactions").insert({"tid": pending_payments[user_id]["tid"], "user_id": user_id}).execute()
                    
                    bot.reply_to(message, f"✅ ቁጥር {num} በተሳካ ሁኔታ ተመዝግቧል! መልካም እድል!")
                    bot.send_message(GROUP_ID, f"🎰 **አዲስ ተጫዋች ተመዝግቧል!**\n👤 ስም፦ {pending_payments[user_id]['name']}\n🎟 የተመረጠ ቁጥር፦ {num}")
                    del pending_payments[user_id]
            except:
                bot.reply_to(message, "⚠️ መመዝገብ አልተቻለም፣ እባክዎ ደግመው ይሞክሩ።")
        else:
            bot.reply_to(message, "❌ እባክዎ ከ 1 እስከ 100 ያለ ቁጥር ብቻ ይላኩ።")
            
    # ሐ. ያልታወቀ መልዕክት
    else:
        bot.reply_to(message, "❌ የተሳሳተ ትዕዛዝ! መመሪያ ለማየት /help ይጫኑ። ለመመዝገብ ደግሞ የባንክ ደረሰኝዎን Forward ያድርጉ።")

# --- 6. ማስጀመሪያ (Background Tasks) ---

def run_scheduler():
    schedule.every(30).minutes.do(send_auto_announcement)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception:
            time.sleep(10)
