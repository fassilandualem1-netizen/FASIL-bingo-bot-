import telebot
from supabase import create_client, Client
import re
import os

# CONFIGURATION
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 8488592165
GROUP_ID = -1003881429974
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)

current_bet_price = 50 
pending_payments = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ሰላም! የ FASIL VIP ቢንጎ ረዳት ነኝ። 🎰\n\nለመጫወት የባንክ መልዕክቱን 'Forward' ያድርጉልኝ።")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = message.chat.id
    text = message.text if message.text else ""

    # ክፍያ መለየት (ለተለያዩ ስልኮች እንዲሰራ ሰፋ ተደርጓል)
    is_payment = any(word in text.lower() for word in ["transferred", "received", "etb", "ብር", "deposited"])
    
    if is_payment:
        amount_match = re.search(r'(?:ETB|ብር|amount)\s*([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
        if amount_match:
            amount = float(amount_match.group(1).replace(',', ''))
            if amount >= current_bet_price:
                slots = int(amount // current_bet_price)
                pending_payments[user_id] = {"name": message.from_user.first_name, "slots": slots}
                bot.reply_to(message, f"✅ የ {amount} ብር ክፍያ ተረጋግጧል! ለ {slots} ቁጥር ይበቃዎታል። እባክዎ ቁጥር ይላኩ።")
                return

    # ቁጥር መመዝገብ
    if user_id in pending_payments and text.isdigit():
        num = int(text)
        if 1 <= num <= 100:
            try:
                supabase.table("bingo_slots").update({"player_name": pending_payments[user_id]["name"], "is_booked": True}).eq("slot_number", num).execute()
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል!")
                pending_payments[user_id]["slots"] -= 1
                if pending_payments[user_id]["slots"] == 0: del pending_payments[user_id]
            except:
                bot.reply_to(message, "⚠️ ስህተት ተፈጠረ። ዳታቤዙን ያረጋግጡ።")
        else:
            bot.reply_to(message, "እባክዎ ከ 1-100 ያለ ቁጥር ይላኩ።")

print("Bot is starting on Hugging Face...")
bot.polling(none_stop=True)
