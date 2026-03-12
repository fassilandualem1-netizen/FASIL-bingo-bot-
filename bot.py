import telebot
from supabase import create_client, Client
import re
import time
import math

# --- CONFIGURATION ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
GROUP_ID = -1003881429974
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

# ያንተ መረጃዎች
MY_NAME = "FASSIL ANDUALEM"
MY_CBE = "1000584461757"
MY_TELEBIRR = "0951381356"

bot = telebot.TeleBot(API_TOKEN, threaded=True) # Threaded ለፈጣን ምላሽ
supabase: Client = create_client(SB_URL, SB_KEY)

BET_PRICE = 50 
pending_payments = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f"ሰላም {message.from_user.first_name}! የ FASIL VIP ቢንጎ ረዳት ነኝ። 🎰\n\nለመጫወት የባንክ መልዕክቱን (CBE/Telebirr) እዚህ ላይ Forward ያድርጉ።")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.chat.id
    text = message.text if message.text else ""
    text_lower = text.lower()

    # 1. ክፍያ ማረጋገጫ (CBE/Telebirr)
    is_bank = any(x in text_lower for x in ["cbe", "telebirr", "received", "transferred"])
    is_for_me = any(x in text_lower for x in [MY_NAME.lower(), MY_CBE, MY_TELEBIRR])

    if is_bank and is_for_me:
        tid_match = re.search(r'(?:txn|id|ማጣቀሻ)\s*(?:no\.|:)?\s*([a-z0-9]+)', text_lower)
        if tid_match:
            tid = tid_match.group(1).upper()
            
            # Duplicate Check (ከዚህ በፊት ጥቅም ላይ መዋሉን ማረጋገጥ)
            check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
            if check.data:
                bot.reply_to(message, "❌ ይህ ማጣቀሻ ቁጥር ቀድሞ ጥቅም ላይ ውሏል!")
                return

            amt_match = re.search(r'(?:etb|ብር|amount)\s*([\d,]+(?:\.\d+)?)', text_lower)
            if amt_match:
                amount = float(amt_match.group(1).replace(',', ''))
                if amount >= (BET_PRICE - 5):
                    slots_to_buy = math.ceil(amount / BET_PRICE)
                    # መዝግብ
                    supabase.table("used_transactions").insert({"tid": tid, "user_id": user_id, "amount": amount}).execute()
                    pending_payments[user_id] = {"name": message.from_user.first_name, "slots": slots_to_buy}
                    
                    bot.reply_to(message, f"✅ የ {amount} ብር ክፍያ ተረጋግጧል! (TID: {tid})\n🎯 እባክዎ {slots_to_buy} ቁጥር/ቁጥሮችን አንድ በአንድ ይላኩ።")
                    return
    
    # 2. ቁጥር መመዝገብ
    if user_id in pending_payments and text.isdigit():
        num = int(text)
        if 1 <= num <= 100:
            # ዳታቤዝ ላይ መኖሩን ቼክ አድርግ
            check_slot = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            if check_slot.data and check_slot.data[0]['is_booked']:
                bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል። እባክዎ ሌላ ይምረጡ።")
            else:
                supabase.table("bingo_slots").update({"player_name": pending_payments[user_id]["name"], "is_booked": True}).eq("slot_number", num).execute()
                pending_payments[user_id]["slots"] -= 1
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                
                if pending_payments[user_id]["slots"] == 0:
                    bot.send_message(user_id, "🏆 ሁሉንም ቁጥሮች መዝግበው ጨርሰዋል። መልካም እድል!")
                    bot.send_message(GROUP_ID, f"🎰 አዲስ ተጫዋች፦ {pending_payments[user_id]['name']}\n🎟 የተያዘ ቁጥር፦ {num}")
                    del pending_payments[user_id]
                else:
                    bot.send_message(user_id, f"ቀሪ {pending_payments[user_id]['slots']} ቁጥር ይላኩ።")
        else:
            bot.reply_to(message, "❌ እባክዎ ከ 1 እስከ 100 ያለ ቁጥር ብቻ ይላኩ።")

# --- START BOT ---
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except:
        time.sleep(5)
