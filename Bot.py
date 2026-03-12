import telebot
from supabase import create_client, Client
import re

# --- CONFIGURATION (የተስተካከሉ መረጃዎች) ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 8488592165
GROUP_ID = -1003881429974
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

# ቦቱን እና ዳታቤዙን እናገናኝ
bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)

# የመደብ ዋጋ (መነሻ 20 ብር)
current_bet_price = 20 
pending_payments = {}

# 1. ቦቱ ሲነሳ (Start)
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ሰላም! የ FASIL VIP ቢንጎ ረዳት ቦት ነኝ። 🎰\n\nለመጫወት የባንክ መልዕክቱን (SMS) እዚህ 'Forward' ያድርጉልኝ።")

# 2. የመደብ ዋጋ መቀየሪያ (ለአንተ ብቻ)
@bot.message_handler(commands=['setprice'])
def set_price(message):
    global current_bet_price
    if message.from_user.id == ADMIN_ID:
        try:
            new_price = int(message.text.split()[1])
            current_bet_price = new_price
            bot.reply_to(message, f"✅ የመደብ ዋጋ ወደ {current_bet_price} ብር ተቀይሯል!")
        except:
            bot.reply_to(message, "ስህተት፡ '/setprice 100' በሚል ይጻፉ።")

# 3. የባንክ መልዕክቶችን ማንበቢያ
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.chat.id
    text = message.text

    # የቴሌብር ወይም የ CBE መልዕክት መሆኑን ቼክ እናድርግ
    is_telebirr = "transferred ETB" in text and "telebirr" in text.lower()
    is_cbe = "credited with ETB" in text or "Banking with CBE" in text

    if is_telebirr or is_cbe:
        # የብር መጠኑን ፈልግ
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
                bot.reply_to(message, f"⚠️ ይቅርታ፣ መደቡ {current_bet_price} ብር ነው። የላኩት ግን {amount} ብር ነው።")
        return

    # 4. ቁጥር መመዝገቢያ (ተጫዋቹ ቁጥር ሲልክ)
    if user_id in pending_payments and text.isdigit():
        num = int(text)
        data = pending_payments[user_id]
        
        if 1 <= num <= 100:
            # ቁጥሩ ቀድሞ ተይዞ እንደሆነ ቼክ አድርግ (ዳታቤዝ ውስጥ)
            check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            
            if check.data and check.data[0]['is_booked']:
                bot.reply_to(message, f"❌ ቁጥር {num} ቀድሞ ተይዟል። እባክዎ ሌላ ቁጥር ይምረጡ።")
            else:
                # ቁጥሩን ያዝ
                data["chosen_numbers"].append(num)
                data["slots_left"] -= 1
                
                # ዳታቤዝ (Supabase) ላይ ሪከርድ አድርግ
                supabase.table("bingo_slots").update({
                    "player_name": data["name"], 
                    "is_booked": True
                }).eq("slot_number", num).execute()

                if data["slots_left"] > 0:
                    bot.reply_to(message, f"✅ ቁጥር {num} ተይዟል።\nገና {data['slots_left']} ቁጥር ይቀረዎታል። ቀጣዩን ይላኩ።")
                else:
                    nums_list = ", ".join(map(str, data["chosen_numbers"]))
                    bot.reply_to(message, f"🎯 ተመዝግቦ ተጠናቋል! የያዟቸው ቁጥሮች፦ {nums_list}")
                    
                    # ግሩፑ ላይ መልዕክት ላክ
                    bot.send_message(GROUP_ID, f"🎰 **አዲስ ተጫዋች ተመዝግቧል!**\n👤 ስም: {data['name']}\n🎟 ቁጥር: {nums_list}\n✅ ሁኔታ: ተከፍሏል")
                    del pending_payments[user_id]
        else:
            bot.reply_to(message, "እባክዎ ከ 1 እስከ 100 ያለ ቁጥር ብቻ ይላኩ።")

# ቦቱ ስራ እንዲጀምር
bot.polling(none_stop=True)
