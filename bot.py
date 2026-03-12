import telebot
from supabase import create_client, Client
import re
import http.server
import socketserver
import threading
import os

# --- 1. RENDER 'PORT' TRICK (ሬንደር እንዳያጠፋው) ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- 2. CONFIGURATION ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 8488592165
GROUP_ID = -1003881429974
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)

current_bet_price = 20 
pending_payments = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ሰላም! የ FASIL VIP ቢንጎ ረዳት ቦት ነኝ። 🎰\n\nለመጫወት የባንክ መልዕክቱን (SMS) 'Forward' ያድርጉልኝ።")

@bot.message_handler(commands=['setprice'])
def set_price(message):
    global current_bet_price
    if message.from_user.id == ADMIN_ID:
        try:
            new_price = int(message.text.split()[1])
            current_bet_price = new_price
            bot.reply_to(message, f"✅ የመደብ ዋጋ ወደ {current_bet_price} ብር ተቀይሯል!")
        except:
            bot.reply_to(message, "ስህተት፡ '/setprice 50' በሚል ይጻፉ።")

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.chat.id
    text = message.text

    # የባንክ መልዕክት መሆኑን ቼክ አድርግ
    is_telebirr = "transferred ETB" in text.lower() or "received ETB" in text.lower()
    is_cbe = "credited with ETB" in text or "Banking with CBE" in text

    if is_telebirr or is_cbe:
        amount_match = re.search(r'ETB\s*(\d+(\.\d+)?)', text)
        if amount_match:
            amount = float(amount_match.group(1))
            if amount >= current_bet_price:
                slots_count = int(amount // current_bet_price)
                pending_payments[user_id] = {
                    "name": message.from_user.first_name,
                    "slots_left": slots_count,
                    "chosen_numbers": []
                }
                bot.reply_to(message, f"✅ የ {amount} ብር ክፍያ ተረጋግጧል!\n🎯 ለ {slots_count} ቁጥር ይበቃዎታል።\nእባክዎ የሚፈልጉትን ቁጥር አንድ በአንድ ይላኩ።")
            else:
                bot.reply_to(message, f"⚠️ መደቡ {current_bet_price} ብር ነው። የላኩት ግን {amount} ብር ነው።")
        return

    # ቁጥር መመዝገቢያ
    if user_id in pending_payments and text.isdigit():
        num = int(text)
        data = pending_payments[user_id]
        
        if 1 <= num <= 100:
            try:
                # ቼክ አድርግ
                check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check.data and check.data[0]['is_booked']:
                    bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል። ሌላ ይምረጡ።")
                else:
                    supabase.table("bingo_slots").update({"player_name": data["name"], "is_booked": True}).eq("slot_number", num).execute()
                    data["chosen_numbers"].append(num)
                    data["slots_left"] -= 1
                    
                    if data["slots_left"] > 0:
                        bot.reply_to(message, f"✅ ቁጥር {num} ተይዟል። ገና {data['slots_left']} ይቀረዎታል።")
                    else:
                        nums_list = ", ".join(map(str, data["chosen_numbers"]))
                        bot.reply_to(message, f"🎯 ተጠናቋል! የያዟቸው ቁጥሮች፦ {nums_list}")
                        bot.send_message(GROUP_ID, f"🎰 **አዲስ ተጫዋች!**\n👤 ስም: {data['name']}\n🎟 ቁጥር: {nums_list}\n✅ ሁኔታ: ተከፍሏል")
                        del pending_payments[user_id]
            except Exception as e:
                bot.reply_to(message, "⚠️ ዳታቤዝ ላይ ስህተት ተፈጠረ። እባክዎ አስተዳዳሪውን ያነጋግሩ።")
        else:
            bot.reply_to(message, "እባክዎ ከ 1 እስከ 100 ያለ ቁጥር ይላኩ።")

bot.polling(none_stop=True)
