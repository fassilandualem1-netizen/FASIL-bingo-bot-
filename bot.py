import telebot
from supabase import create_client, Client
import re
import http.server
import socketserver
import threading
import os

# --- 1. RENDER PORT TRICK (አፕሊኬሽኑ እንዳይዘጋ) ---
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

# --- 3. COMMANDS ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ሰላም! የ FASIL VIP ቢንጎ ረዳት ቦት ነኝ። 🎰\n\nለመጫወት የባንክ መልዕክቱን 'Forward' ያድርጉልኝ።")

@bot.message_handler(commands=['setprice'])
def set_price(message):
    global current_bet_price
    if message.from_user.id == ADMIN_ID:
        try:
            current_bet_price = int(message.text.split()[1])
            bot.reply_to(message, f"✅ የመደብ ዋጋ ወደ {current_bet_price} ብር ተቀይሯል!")
        except:
            bot.reply_to(message, "ትክክለኛ ዋጋ ያስገቡ። ለምሳሌ፦ /setprice 50")

@bot.message_handler(commands=['reset_game'])
def reset_game(message):
    if message.from_user.id == ADMIN_ID:
        try:
            # ሁሉንም ቁጥሮች ነፃ ማድረግ
            supabase.table("bingo_slots").update({"player_name": None, "is_booked": False}).neq("slot_number", 0).execute()
            # ያገለገሉ ደረሰኞችን ዝርዝር ማጽዳት
            supabase.table("used_transactions").delete().neq("transaction_id", "EMPTY").execute()
            bot.reply_to(message, "♻️ ጨዋታው ጸድቷል! አዲስ ዙር መጀመር ይቻላል።")
        except Exception as e:
            bot.reply_to(message, f"ስህተት፡ {str(e)}")

# --- 4. MAIN WORKER (ክፍያ ቼክ አድርጎ መመዝገብ) ---

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.chat.id
    text = message.text

    # ሀ. መዝገብ ማየት
    if text == "መዝገብ":
        try:
            res = supabase.table("bingo_slots").select("*").eq("is_booked", True).execute()
            if res.data:
                msg = "📝 **የተመዘገቡ ተጫዋቾች፦**\n\n"
                for row in res.data:
                    msg += f"🎰 ቁጥር {row['slot_number']} - {row['player_name']}\n"
                bot.reply_to(message, msg, parse_mode="Markdown")
            else:
                bot.reply_to(message, "እስካሁን የተመዘገበ የለም።")
        except:
            bot.reply_to(message, "መዝገቡን ማምጣት አልተቻለም።")
        return

    # ለ. የባንክ መልዕክት መለየት
    is_bank = any(k in text.lower() for k in ["transferred", "received", "telebirr", "cbe"])
    if is_bank:
        amount_match = re.search(r'(?:ETB|ብር)\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        tid_match = re.search(r'(?:transaction number|transaction id|Trx ID:)\s*([A-Z0-9]+)', text, re.IGNORECASE)
        
        # የእርስዎ ስልክ (1356) በመልዕክቱ ውስጥ መኖሩን ማረጋገጥ
        if amount_match and tid_match and "1356" in text:
            amount = float(amount_match.group(1))
            tid = tid_match.group(1)

            # ደረሰኙ ተደግሞ እንደሆነ ቼክ ማድረግ
            check = supabase.table("used_transactions").select("*").eq("transaction_id", tid).execute()
            if check.data:
                bot.reply_to(message, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል!")
                return

            if amount >= current_bet_price:
                # ደረሰኙን መመዝገብ
                supabase.table("used_transactions").insert({"transaction_id": tid}).execute()
                
                slots = int(amount // current_bet_price)
                pending_payments[user_id] = {
                    "name": f"{message.from_user.first_name} ({message.from_user.id})",
                    "slots_left": slots,
                    "chosen": []
                }
                bot.reply_to(message, f"✅ የ {amount} ብር ክፍያ ተረጋግጧል!\n🎯 ለ {slots} ቁጥር ይበቃዎታል።\n\nእባክዎ የሚፈልጉትን ቁጥር ይላኩ።")
            else:
                bot.reply_to(message, f"⚠️ መደቡ {current_bet_price} ብር ነው። የላኩት ግን {amount} ብር ነው።")
        elif is_bank and "1356" not in text:
            bot.reply_to(message, "❌ ደረሰኙ ወደ ትክክለኛው ቁጥር (1356) የተላከ አይደለም።")
        return

    # ሐ. የቁጥር ምርጫን በስም/በስልክ መመዝገብ
    if user_id in pending_payments and text.isdigit():
        num = int(text)
        data = pending_payments[user_id]
        
        if 1 <= num <= 100:
            try:
                # ቁጥሩ ቀድሞ ተይዞ እንደሆነ ማየት
                check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check.data and check.data[0]['is_booked']:
                    bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል። ሌላ ይምረጡ።")
                else:
                    # ዳታቤዝ ላይ በስም/በID መመዝገብ
                    supabase.table("bingo_slots").update({"player_name": data["name"], "is_booked": True}).eq("slot_number", num).execute()
                    data["chosen"].append(num)
                    data["slots_left"] -= 1
                    
                    if data["slots_left"] > 0:
                        bot.reply_to(message, f"✅ ቁጥር {num} ተይዟል። ገና {data['slots_left']} ምርጫ ይቀረዎታል።")
                    else:
                        nums_list = ", ".join(map(str, data["chosen"]))
                        bot.reply_to(message, f"🎯 ምዝገባ ተጠናቋል! የያዟቸው ቁጥሮች፦ {nums_list}")
                        # ለግሩፑ ሪፖርት መላክ
                        bot.send_message(GROUP_ID, f"🎰 **አዲስ ተጫዋች!**\n👤 ስም/ID: {data['name']}\n🎟 ቁጥሮች: {nums_list}\n✅ ክፍያ: ተረጋግጧል")
                        del pending_payments[user_id]
            except:
                bot.reply_to(message, "⚠️ ዳታቤዝ ላይ መመዝገብ አልተቻለም።")
        else:
            bot.reply_to(message, "እባክዎ ከ 1 እስከ 100 ያለ ቁጥር ብቻ ይላኩ።")

bot.polling(none_stop=True)
