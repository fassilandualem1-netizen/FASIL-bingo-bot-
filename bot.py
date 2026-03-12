import telebot
from supabase import create_client, Client
import re
import http.server
import socketserver
import threading
import os

# --- 1. RENDER PORT TRICK ---
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
    bot.reply_to(message, "ሰላም! የ FASIL VIP ቢንጎ ረዳት ቦት ነኝ። 🎰\n\nለመጫወት የባንክ መልዕክቱን 'Forward' ያድርጉልኝ።")

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

    # --- ሀ. የ"መዝገብ" ትዕዛዝ ---
    if text == "መዝገብ":
        try:
            response = supabase.table("bingo_slots").select("*").eq("is_booked", True).execute()
            if response.data:
                msg = "📝 **የተመዘገቡ ተጫዋቾች ዝርዝር፦**\n\n"
                for row in response.data:
                    msg += f"👤 {row['player_name']} 🎟 ቁጥር: {row['slot_number']}\n"
                bot.reply_to(message, msg, parse_mode="Markdown")
            else:
                bot.reply_to(message, "እስካሁን የተመዘገበ ተጫዋች የለም።")
        except:
            bot.reply_to(message, "⚠️ መዝገቡን ማምጣት አልተቻለም።")
        return

    # --- ለ. የባንክ መልዕክት መለየት እና ማረጋገጥ ---
    is_bank_msg = any(keyword in text.lower() for keyword in ["transferred", "received", "credited", "telebirr", "cbe"])
    
    if is_bank_msg:
        amount_match = re.search(r'(?:ETB|ብር)\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        tid_match = re.search(r'transaction number is ([A-Z0-9]+)', text, re.IGNORECASE)
        is_correct_receiver = "1356" in text # የእርስዎ ስልክ ቁጥር ማረጋገጫ

        if amount_match and tid_match and is_correct_receiver:
            amount = float(amount_match.group(1))
            tid = tid_match.group(1)

            try:
                # ደረሰኙ ቀድሞ ጥቅም ላይ መዋሉን ቼክ ማድረግ
                check_tid = supabase.table("used_transactions").select("transaction_id").eq("transaction_id", tid).execute()
                if check_tid.data:
                    bot.reply_to(message, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል!")
                    return

                if amount >= current_bet_price:
                    # አዲስ ትራንዛክሽን ከሆነ መመዝገብ
                    supabase.table("used_transactions").insert({"transaction_id": tid}).execute()
                    
                    slots_count = int(amount // current_bet_price)
                    pending_payments[user_id] = {
                        "name": message.from_user.first_name,
                        "slots_left": slots_count,
                        "chosen_numbers": []
                    }
                    bot.reply_to(message, f"✅ የ {amount} ብር ክፍያ ተረጋግጧል! (ID: {tid})\n🎯 ለ {slots_count} ቁጥር ይበቃዎታል።\n\nእባክዎ የሚፈልጉትን ቁጥር አሁን ይላኩ።")
                else:
                    bot.reply_to(message, f"⚠️ መደቡ {current_bet_price} ብር ነው። የላኩት ግን {amount} ብር ነው።")
            except Exception:
                bot.reply_to(message, "⚠️ የዳታቤዝ ስህተት (ምናልባት used_transactions Table አልተፈጠረም)።")
        elif is_bank_msg and not is_correct_receiver:
            bot.reply_to(message, "❌ ስህተት፡ ደረሰኙ ወደ ትክክለኛው ቁጥር (1356) የተላከ አይደለም።")
        return

    # --- ሐ. የቁጥር ምርጫ ---
    if user_id in pending_payments and text.isdigit():
        num = int(text)
        data = pending_payments[user_id]
        
        if 1 <= num <= 100:
            try:
                check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check.data and check.data[0]['is_booked']:
                    bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል። ሌላ ይምረጡ።")
                else:
                    supabase.table("bingo_slots").update({"player_name": data["name"], "is_booked": True}).eq("slot_number", num).execute()
                    data["chosen_numbers"].append(num)
                    data["slots_left"] -= 1
                    
                    if data["slots_left"] > 0:
                        bot.reply_to(message, f"✅ ቁጥር {num} ተይዟል። ገና {data['slots_left']} ምርጫ ይቀረዎታል።")
                    else:
                        nums_list = ", ".join(map(str, data["chosen_numbers"]))
                        bot.reply_to(message, f"🎯 ተጠናቋል! የያዟቸው ቁጥሮች፦ {nums_list}")
                        bot.send_message(GROUP_ID, f"🎰 **አዲስ ተጫዋች!**\n👤 ስም: {data['name']}\n🎟 ቁጥሮች: {nums_list}\n✅ ክፍያ: ተረጋግጧል")
                        del pending_payments[user_id]
            except Exception:
                bot.reply_to(message, "⚠️ የቴክኒክ ስህተት ተፈጠረ።")
        else:
            bot.reply_to(message, "እባክዎ ከ 1 እስከ 100 ያለ ቁጥር ብቻ ይላኩ።")

bot.polling(none_stop=True)
