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
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
app = Flask('')

ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 
user_state = {}

# --- 2. KEEP-ALIVE ---
@app.route('/')
def home(): return "Fasil Bingo Online!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): Thread(target=run_flask).start()

# --- 3. HELPERS ---
def get_price():
    try:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        return float(res.data[0]['value']) if res.data else 20.0
    except: return 20.0

def get_balance(u_id):
    try:
        res = supabase.table("users").select("balance").eq("user_id", str(u_id)).execute()
        return float(res.data[0]['balance']) if res.data else 0.0
    except: return 0.0

def verify_sms(text):
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

# --- 4. BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = str(message.from_user.id)
    try:
        supabase.table("users").upsert({"user_id": u_id, "username": message.from_user.username}).execute()
        
        if message.chat.id == ADMIN_ID:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("📊 ሪፖርት", "🔄 Reset", "💰 ዋጋ ቀይር")
            bot.send_message(message.chat.id, "ሰላም ፋሲል! ቦቱ ከዳታቤዙ ጋር በሚገባ ተናቧል።", reply_markup=markup)
        else:
            bal = get_balance(u_id)
            price = get_price()
            bot.send_message(message.chat.id, f"🎰 **ፋሲል ቢንጎ**\n\n💵 Wallet፦ **{bal} ብር**\n🎟 የዕጣ ዋጋ፦ **{price} ብር**\n\nለመመዝገብ የባንክ SMS እዚህ ይላኩ። (የ30 ደቂቃ ገደብ አለው)", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "⚠️ ዳታቤዙን ማግኘት አልቻልኩም። እባክዎ ደግመው ይሞክሩ።")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    u_id = message.chat.id
    txt = message.text

    # --- ADMIN ---
    if u_id == ADMIN_ID and txt == "🔄 Reset":
        supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
        bot.reply_to(message, "✅ ሰሌዳው ጸድቷል!")
        return

    # --- SMS PROCESS ---
    tid, amt = verify_sms(txt)
    if tid == "EXPIRED":
        bot.reply_to(message, "❌ ደረሰኙ ከ30 ደቂቃ በላይ ስለቆየ አይሰራም።")
        return
    if tid:
        check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
        if check.data: return bot.reply_to(message, "❌ ይህ ደረሰኝ ጥቅም ላይ ውሏል!")
        
        new_bal = get_balance(u_id) + amt
        supabase.table("users").update({"balance": new_bal}).eq("user_id", str(u_id)).execute()
        supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id), "amount": amt}).execute()
        
        user_state[u_id] = {"step": "name"}
        bot.reply_to(message, f"✅ {amt} ብር Wallet ውስጥ ገብቷል!\nጠቅላላ፦ {new_bal} ብር\n\nአሁን ስምዎን ይላኩ።")
        return

    # --- REGISTRATION ---
    if u_id in user_state and user_state[u_id].get("step") == "name":
        user_state[u_id]["name"] = txt
        user_state[u_id]["step"] = "pick"
        res = supabase.table("bingo_slots").select("slot_number, is_booked").order("slot_number").execute()
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton("❌" if r['is_booked'] else f"{r['slot_number']}", 
                callback_data=f"pick_{r['slot_number']}" if not r['is_booked'] else "booked") for r in res.data]
        markup.add(*btns)
        bot.send_message(u_id, f"እሺ {txt}! ቁጥር ይምረጡ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    u_id = call.message.chat.id
    if call.data.startswith("pick_") and u_id in user_state:
        price = get_price()
        bal = get_balance(u_id)
        if bal < price:
            bot.answer_callback_query(call.id, "❌ በቂ Wallet የሎትም!", show_alert=True)
            return
        
        num = int(call.data.split("_")[1])
        new_bal = bal - price
        supabase.table("users").update({"balance": new_bal}).eq("user_id", str(u_id)).execute()
        supabase.table("bingo_slots").update({"player_name": user_state[u_id]["name"], "is_booked": True}).eq("slot_number", num).execute()
        
        bot.edit_message_text(f"✅ ተመዝግቧል! ቁጥር፦ {num}\nቀሪ፦ {new_bal} ብር", chat_id=u_id, message_id=call.message.message_id)
        bot.send_message(GROUP_ID, f"🎟 አዲስ ምዝገባ፦ {user_state[u_id]['name']} | ቁጥር፦ {num}")
        
        if new_bal >= price:
            bot.send_message(u_id, "ሌላ ቁጥር መምረጥ ይችላሉ።", reply_markup=call.message.reply_markup)
        else:
            del user_state[u_id]

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
