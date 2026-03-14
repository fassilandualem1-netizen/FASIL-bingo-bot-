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

# --- 3. HELPERS ---
def get_user_balance(u_id):
    try:
        res = supabase.table("users").select("balance").eq("user_id", str(u_id)).execute()
        return float(res.data[0]['balance']) if res.data else 0.0
    except: return 0.0

def get_ticket_price():
    try:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        return float(res.data[0]['value']) if res.data else 20.0
    except: return 20.0 # ዳታቤዙ ባይሰራ እንኳን 20 ብር ይጠቀማል

def verify_gasha_sms(text):
    text = text.upper()
    now = datetime.now()
    tid = re.search(r'(?:ID|TXN|G-|FT)[:\s]*([A-Z0-9]{6,16})', text)
    amt = re.search(r'(?:BIRR|ETB|ብር|AMT)[:\s]*([\d\.]+)', text)
    date_m = re.search(r'(\d{2}/\d{2}/\d{4})', text)
    time_m = re.search(r'(\d{2}:\d{2}(?::\d{2})?)', text)

    if tid and amt and date_m and time_m:
        try:
            sms_dt = datetime.strptime(f"{date_m.group(1)} {time_m.group(1)}", "%d/%m/%Y %H:%M:%S" if ":" in time_m.group(1).split(":")[-1] else "%d/%m/%Y %H:%M")
            if (now - sms_dt) > timedelta(minutes=30): return "EXPIRED", None
            return tid.group(1), float(amt.group(1))
        except: return None, None
    return None, None

def get_bingo_board_markup():
    markup = types.InlineKeyboardMarkup(row_width=5)
    try:
        res = supabase.table("bingo_slots").select("slot_number, is_booked").order("slot_number").execute()
        btns = [types.InlineKeyboardButton("❌" if r['is_booked'] else f"{r['slot_number']}", 
                callback_data=f"pick_{r['slot_number']}" if not r['is_booked'] else "booked") for r in res.data]
        markup.add(*btns)
    except: pass
    return markup

# --- 4. BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    try:
        u_id = str(message.from_user.id)
        # ተጠቃሚውን መመዝገብ
        supabase.table("users").upsert({"user_id": u_id, "username": message.from_user.username}).execute()
        
        if message.chat.id == ADMIN_ID:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("📊 ሪፖርት", "🔄 Reset", "💰 Set Price")
            bot.send_message(message.chat.id, "ሰላም አድሚን! ስራ ለመጀመር ዝግጁ ነኝ።", reply_markup=markup)
        else:
            balance = get_user_balance(u_id)
            price = get_ticket_price()
            desc = f"🎰 **እንኳን ወደ ፋሲል ቢንጎ በሰላም መጡ!**\n\n💵 ቀሪ ሂሳብ፦ **{balance} ብር**\n🎟 የዕጣ ዋጋ፦ **{price} ብር**\n\n🏦 **CBE:** `1000XXXXXXXX` \n📲 **Telebirr/Gasha:** `09XXXXXXXX` \n\n⚠️ ለመሳተፍ ከባንክ የደረሰዎትን SMS እዚህ ይላኩ።"
            bot.send_message(message.chat.id, desc, parse_mode="Markdown")
    except Exception as e:
        print(f"Start Error: {e}")
        bot.send_message(message.chat.id, "ሰላም! ቦቱ ዝግጁ ነው፣ እባክዎ SMS ይላኩ።")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    u_id = message.chat.id
    txt = message.text

    # --- ADMIN ACTIONS ---
    if u_id == ADMIN_ID:
        if txt == "📊 ሪፖርት":
            # ሪፖርት logic...
            bot.reply_to(message, "ሪፖርት እያዘጋጀሁ ነው...")
            return
        elif txt == "🔄 Reset":
            supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
            bot.reply_to(message, "ሰሌዳው ጽድቷል።")
            return

    # --- SMS LOGIC ---
    tid, amt = verify_gasha_sms(txt)
    if tid == "EXPIRED":
        return bot.reply_to(message, "❌ ደረሰኙ ከ30 ደቂቃ በላይ ስለቆየ አይሰራም።")
    
    if tid:
        try:
            check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
            if check.data: return bot.reply_to(message, "❌ ይህ ደረሰኝ ጥቅም ላይ ውሏል!")
            
            # Wallet ማሳደግ
            current_bal = get_user_balance(u_id)
            new_bal = current_bal + amt
            supabase.table("users").update({"balance": new_bal}).eq("user_id", str(u_id)).execute()
            supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id), "amount": amt}).execute()
            
            user_state[u_id] = {"step": "get_name"}
            bot.reply_to(message, f"✅ {amt} ብር Wallet ውስጥ ገብቷል!\nጠቅላላ፦ {new_bal} ብር\n\nአሁን ስምዎን ይላኩ።")
        except:
            bot.reply_to(message, "❌ ስህተት ተፈጥሯል፣ እባክዎ ደግመው ይሞክሩ።")
        return

    # --- REGISTRATION ---
    if u_id in user_state and user_state[u_id].get("step") == "get_name":
        user_state[u_id]["name"] = txt
        user_state[u_id]["step"] = "pick_number"
        bot.send_message(u_id, f"እሺ {txt}! ቁጥር ይምረጡ፦", reply_markup=get_bingo_board_markup())

# --- 5. CALLBACK (BUTTONS) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    u_id = call.message.chat.id
    if call.data.startswith("pick_") and u_id in user_state:
        price = get_ticket_price()
        balance = get_user_balance(u_id)
        
        if balance < price:
            bot.answer_callback_query(call.id, "❌ በቂ ገንዘብ የለም!", show_alert=True)
            return

        num = int(call.data.split("_")[1])
        new_bal = balance - price
        
        # ዳታቤዝ ማስተካከል
        supabase.table("users").update({"balance": new_bal}).eq("user_id", str(u_id)).execute()
        supabase.table("bingo_slots").update({"player_name": user_state[u_id]["name"], "is_booked": True}).eq("slot_number", num).execute()
        
        bot.edit_message_text(f"✅ ተመዝግቧል! ቁጥር፦ {num}\nቀሪ፦ {new_bal} ብር", chat_id=u_id, message_id=call.message.message_id)
        bot.send_message(GROUP_ID, f"🎟 አዲስ ምዝገባ፦ {user_state[u_id]['name']} | ቁጥር፦ {num}")
        
        if new_bal < price: del user_state[u_id]
        else: bot.send_message(u_id, "ሌላ ቁጥር መምረጥ ይችላሉ፦", reply_markup=get_bingo_board_markup())

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
