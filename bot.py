import telebot
from supabase import create_client, Client
import re, time, os, threading, schedule
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

MY_NAMES = ["fasil", "fassil", "andualem", "fassil andualem", "fasil andualem"]
MY_CBE = "1000584461757"
MY_TELEBIRR = "0951381356"

pending_payments = {}
last_board_msg_id = None # በግሩፑ ላይ ያለውን ሰንጠረዥ ለመቆጣጠር

# --- 3. የቢንጎ ሰንጠረዥ ፈጣሪ ---
def generate_board():
    try:
        res = supabase.table("bingo_slots").select("slot_number", "is_booked").order("slot_number").execute()
        board = "🎰 **FASIL VIP BINGO BOARD** 🎰\n\n"
        row_text = ""
        for i, row in enumerate(res.data):
            status = "❌" if row['is_booked'] else f"{row['slot_number']:02d}"
            row_text += f"| {status} "
            if (i + 1) % 5 == 0:
                board += row_text + "|\n"
                row_text = ""
        
        res_booked = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).execute()
        board += f"\n🎟 የቀሩ ክፍት ቦታዎች፦ {len(res_booked.data)}"
        board += "\n💰 ለመመዝገብ @Fasil_Bingo_Bot ን ይጠቀሙ"
        return board
    except: return None

def update_group_board():
    global last_board_msg_id
    new_board = generate_board()
    if not new_board: return

    try:
        if last_board_msg_id:
            bot.edit_message_text(new_board, GROUP_ID, last_board_msg_id, parse_mode="Markdown")
        else:
            msg = bot.send_message(GROUP_ID, new_board, parse_mode="Markdown")
            last_board_msg_id = msg.message_id
    except:
        # መልዕክቱ ኤዲት ካልሆነ አዲስ ይላካል
        msg = bot.send_message(GROUP_ID, new_board, parse_mode="Markdown")
        last_board_msg_id = msg.message_id

# --- 4. Validation ---
def is_valid_bank_sms(text):
    text = text.lower()
    if any(k in text for k in ['recharge', 'airtime', 'ካርድ']): return False
    has_bank = any(k in text for k in ['cbe', 'telebirr', 'birr', 'ብር', 'transferred', 'received'])
    has_my_info = any(n in text for n in MY_NAMES) or MY_CBE in text or MY_TELEBIRR in text
    return has_bank and has_my_info

# --- 5. Bot Handlers ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = "ሰላም! የ FASIL VIP ቢንጎ ቦት ነው። 🎰\n\n💰 ለመመዝገብ የባንክ መልዕክቱን Forward ያድርጉ።"
    bot.reply_to(message, text)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = message.chat.id
    text = message.text or ""

    # ሀ. ክፍያ ማረጋገጥ
    if is_valid_bank_sms(text):
        bot.reply_to(message, "⏳ መልዕክቱ ደርሶኛል፣ እያረጋገጥኩ ነው...")
        tid_match = re.search(r'(?i)(?:txn|id|ማጣቀሻ|Ref|Reference|ቁጥር|TxnID)\s*(?:no\.|:)?\s*([a-z0-9]+)', text)
        
        if tid_match:
            tid = tid_match.group(1).upper()
            try:
                check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
                if check.data:
                    bot.reply_to(message, "❌ ይህ ማጣቀሻ ቁጥር (TID) ቀደም ብሎ ጥቅም ላይ ውሏል!")
                    return
                
                pending_payments[user_id] = {"tid": tid, "step": "awaiting_name"}
                bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! እባክዎ በቢንጎው ሰንጠረዥ ላይ እንዲሰፍር የሚፈልጉትን ስም ይላኩ።")
            except: bot.reply_to(message, "⚠️ የዳታቤዝ ስህተት።")
        else: bot.reply_to(message, "❌ ማጣቀሻ ቁጥር አልተገኘም።")

    # ለ. ስም መቀበል
    elif user_id in pending_payments and pending_payments[user_id]["step"] == "awaiting_name":
        pending_payments[user_id]["player_name"] = text
        pending_payments[user_id]["step"] = "awaiting_number"
        bot.reply_to(message, f"ደስ ይላል {text}! አሁን ደግሞ ከ 1-100 ያለውን የሚፈልጉትን ቁጥር ይላኩ።")

    # ሐ. ቁጥር መቀበል
    elif user_id in pending_payments and pending_payments[user_id]["step"] == "awaiting_number" and text.isdigit():
        num = int(text)
        if 1 <= num <= 100:
            try:
                check_slot = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check_slot.data and check_slot.data[0]['is_booked']:
                    bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል። እባክዎ ሌላ ይምረጡ።")
                else:
                    name = pending_payments[user_id]["player_name"]
                    tid = pending_payments[user_id]["tid"]
                    
                    # መመዝገብ
                    supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                    supabase.table("used_transactions").insert({"tid": tid, "user_id": user_id}).execute()
                    
                    bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል! መልካም እድል!")
                    
                    # ግሩፑ ላይ ማስታወቅና ሰንጠረዡን ኤዲት ማድረግ
                    bot.send_message(GROUP_ID, f"🎰 **አዲስ ተጫዋች!**\n👤 ስም፦ {name}\n🎟 ቁጥር፦ {num}")
                    update_group_board() # ቦርዱን Edit ያደርጋል
                    
                    del pending_payments[user_id]
            except: bot.reply_to(message, "⚠️ ስህተት አጋጥሟል።")
        else: bot.reply_to(message, "❌ ከ 1-100 ያለ ቁጥር ብቻ ይላኩ።")
    
    else:
        if message.chat.type == "private":
            bot.reply_to(message, "❌ የተሳሳተ ትዕዛዝ! መመሪያ ለማየት /help ይጠቀሙ።")

# --- 6. Background Tasks ---
def run_scheduler():
    # በየ 30 ደቂቃው አዲስ ሰንጠረዥ ግሩፑ ላይ እንዲላክ (ኤዲት እንዳይሰለች)
    schedule.every(30).minutes.do(update_group_board)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # ቦቱ ሲጀምር ቦርዱን ግሩፕ ላይ እንዲልክ
    try: update_group_board()
    except: pass
    
    bot.polling(none_stop=True)
