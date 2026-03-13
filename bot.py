import telebot
from supabase import create_client, Client
import re, time, os, threading, schedule, math
from flask import Flask

# --- 1. Flask ለ Render ---
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

# እዚህ ጋር ስምህን ከሁለቱም 'Fassil' ጋር እንዲዛመድ አስተካክለነዋል
MY_NAMES = ["fassil", "fasil"] 
MY_CBE = "1000584461757"
MY_TELEBIRR = "0951381356"
BET_PRICE = 50 

pending_payments = {}

# --- 3. አጋዥ ተግባራት ---
def is_valid_bank_sms(text):
    text = text.lower()
    if any(k in text for k in ['recharge', 'airtime', 'ካርድ']): return False
    has_bank = any(k in text for k in ['cbe', 'telebirr', 'birr', 'ብር', 'transferred', 'received'])
    # ያንተ ስም ወይም ስልክ ቁጥር መኖሩን ማረጋገጥ
    has_my_info = any(n in text for n in MY_NAMES) or MY_CBE in text or MY_TELEBIRR in text
    return has_bank and has_my_info

# --- 4. የቦት ትዕዛዞች ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = "ሰላም! የ FASIL VIP ቢንጎ ቦት ነው። 🎰\n\n📖 መመሪያ: /howtoplay\n🎟 የቢንጎ ቦርድ: /viewslot\n🎫 የገዙት ቁጥር: /my_tickets\n💰 ለመመዝገብ: የክፍያ መልዕክቱን Forward ያድርጉ።"
    bot.reply_to(message, text)

@bot.message_handler(commands=['howtoplay'])
def how_to_play(message):
    text = "📖 **እንዴት መጫወት ይቻላል?**\n\n1. በ CBE ወይም Telebirr ክፍያ ይፈጽሙ።\n2. የደረሰኝ መልዕክቱን (SMS) ለዚህ ቦት Forward ያድርጉ።\n3. ቦቱ ክፍያውን ሲያረጋግጥ ቁጥር እንዲመርጡ ይጠይቅዎታል።\n4. ከ 1-100 ያለ ቁጥር ይላኩ።"
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

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = message.chat.id
    text = message.text or ""

    if is_valid_bank_sms(text):
        tid_match = re.search(r'(?i)(?:txn|id|id:|ቁጥር|Ref|Reference)\s*(?:no\.|:)?\s*([a-z0-9]+)', text)
        if tid_match:
            tid = tid_match.group(1).upper()
            try:
                check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
                if check.data:
                    bot.reply_to(message, "❌ ይህ ማጣቀሻ ቁጥር ጥቅም ላይ ውሏል!")
                    return
                # ክፍያውን መመዝገብ
                supabase.table("used_transactions").insert({"tid": tid, "user_id": user_id}).execute()
                pending_payments[user_id] = {"name": message.from_user.first_name, "slots": 1}
                bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! አሁን ቁጥር (1-100) ይላኩ።")
            except: bot.reply_to(message, "⚠️ የዳታቤዝ ስህተት።")
        else: bot.reply_to(message, "❌ ማጣቀሻ ቁጥር (TID) አልተገኘም።")
    
    elif user_id in pending_payments and text.isdigit():
        num = int(text)
        if 1 <= num <= 100:
            try:
                check_slot = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check_slot.data and check_slot.data[0]['is_booked']:
                    bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል።")
                else:
                    supabase.table("bingo_slots").update({"player_name": pending_payments[user_id]["name"], "is_booked": True}).eq("slot_number", num).execute()
                    bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                    bot.send_message(GROUP_ID, f"🎰 አዲስ ተጫዋች!\n👤 ስም፦ {pending_payments[user_id]['name']}\n🎟 ቁጥር፦ {num}")
                    del pending_payments[user_id]
            except: bot.reply_to(message, "⚠️ ስህተት ተፈጥሯል።")
        else: bot.reply_to(message, "❌ ከ 1-100 ያለ ቁጥር ብቻ ይላኩ።")
    else:
        bot.reply_to(message, "❌ የተሳሳተ ትዕዛዝ! እባክዎ /help ይጠቀሙ።")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.polling(none_stop=True)
