import telebot
from telebot import types
from supabase import create_client, Client
from flask import Flask
from threading import Thread
import time, re, os
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
app = Flask('')

user_state = {} 
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 

# --- 2. UPTIMEROBOT (KEEP-ALIVE) ---
@app.route('/')
def home(): return "Fasil Bingo Active!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): Thread(target=run_flask).start()

# --- 3. SMS VERIFICATION LOGIC (GASHA FILTER) ---
def verify_gasha_sms(text):
    text = text.upper()
    now = datetime.now()
    
    # TID, Amount, Date እና Time መፈለጊያ
    tid_match = re.search(r'(?:ID|TXN|G-|FT)[:\s]*([A-Z0-9]{6,16})', text)
    amt_match = re.search(r'(?:BIRR|ETB|ብር|AMT)[:\s]*([\d\.]+)', text)
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    time_match = re.search(r'(\d{2}:\d{2}(?::\d{2})?)', text)

    if tid_match and amt_match and date_match and time_match:
        tid = tid_match.group(1)
        amt = float(amt_match.group(1))
        
        # የ SMS ሰዓቱን ወደ Python datetime መቀየር
        sms_time_str = f"{date_match.group(1)} {time_match.group(1)}"
        try:
            sms_dt = datetime.strptime(sms_time_str, "%d/%m/%Y %H:%M:%S")
        except:
            sms_dt = datetime.strptime(sms_time_str, "%d/%m/%Y %H:%M")

        # የ30 ደቂቃ ገደብ ቼክ
        time_diff = now - sms_dt
        if time_diff > timedelta(minutes=30) or time_diff < timedelta(seconds=-60):
            return "EXPIRED", None
        
        return tid, amt
    return None, None

# --- 4. BOARD MARKUP ---
def get_bingo_board_markup():
    markup = types.InlineKeyboardMarkup(row_width=5)
    res = supabase.table("bingo_slots").select("slot_number, is_booked").order("slot_number").execute()
    btns = [types.InlineKeyboardButton("❌" if r['is_booked'] else f"{r['slot_number']}", 
            callback_data=f"pick_{r['slot_number']}" if not r['is_booked'] else "booked") for r in res.data]
    markup.add(*btns)
    return markup

# --- 5. BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 ሪፖርት", "🔄 Reset", "💰 Set Price")
        bot.send_message(message.chat.id, "ሰላም አድሚን! ስራ ለመጀመር ዝግጁ ነኝ።", reply_markup=markup)
    else:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        price = res.data[0]['value'] if res.data else "20"
        desc = f"🎰 **ፋሲል ቢንጎ**\n\n💰 ዋጋ፦ **{price} ብር**\n🏦 **CBE:** `1000XXXXXXXX` \n📲 **Telebirr/Gasha:** `09XXXXXXXX` \n\n⚠️ SMS እዚህ ይላኩ። (ደረሰኝ ከ30 ደቂቃ በላይ መቆየት የለበትም)"
        bot.send_message(message.chat.id, desc, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    u_id = message.chat.id
    txt = message.text

    # የአድሚን ትዕዛዞች (ሪፖርት፣ Reset ወዘተ እዚህ ይገባሉ...)
    
    # የክፍያ SMS ማረጋገጫ
    tid, amt = verify_gasha_sms(txt)
    
    if tid == "EXPIRED":
        bot.reply_to(message, "❌ ይቅርታ፣ የላኩት ደረሰኝ ከ30 ደቂቃ በላይ ስለቆየ ወይም የዛሬ ስላልሆነ ተቀባይነት የለውም።")
        return
    
    if tid:
        bot.reply_to(message, "⏳ ደረሰኙን እያረጋገጥኩ ነው...")
        check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
        if check.data:
            return bot.reply_to(message, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል!")
        
        user_state[u_id] = {"tid": tid, "amt": amt, "step": "get_name", "time": datetime.now()}
        bot.reply_to(message, "✅ ክፍያዎ ተረጋግጧል! እባክዎ ሙሉ ስምዎን ይላኩ።")
        return

    # ስም መቀበል
    if u_id in user_state and user_state[u_id]["step"] == "get_name":
        user_state[u_id]["name"] = txt
        user_state[u_id]["step"] = "pick_number"
        bot.send_message(u_id, f"እሺ {txt}! አሁን ከሰሌዳው ላይ ቁጥር ይምረጡ፦", reply_markup=get_bingo_board_markup())

# --- 6. CALLBACK (ቁጥር መምረጥ) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    u_id = call.message.chat.id
    if call.data.startswith("pick_") and u_id in user_state:
        num = int(call.data.split("_")[1])
        state = user_state[u_id]
        
        # ዳታቤዝ መመዝገብ
        supabase.table("bingo_slots").update({"player_name": state["name"], "is_booked": True}).eq("slot_number", num).execute()
        supabase.table("used_transactions").insert({"tid": state["tid"], "user_id": str(u_id), "amount": state["amt"]}).execute()
        
        bot.edit_message_text(f"✅ ተመዝግቧል! ቁጥር፦ {num}", chat_id=u_id, message_id=call.message.message_id)
        bot.send_message(GROUP_ID, f"🎟 **አዲስ ምዝገባ!**\n👤 ስም፦ {state['name']}\n🔢 ቁጥር፦ {num}")
        del user_state[u_id]

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
