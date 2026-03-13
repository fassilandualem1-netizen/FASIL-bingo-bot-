import telebot
from supabase import create_client, Client
import re, time, os, threading
import requests
from flask import Flask
from telebot import types
from datetime import datetime

# --- 1. CONFIGURATION ---
API_TOKEN = '8721334129:AAGmSeFapCG6pg2GcOvmhTphIRTCjx_rU-E'
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"
RENDER_URL = "https://fasil-bingo-bot-assistant.onrender.com"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}
admin_states = {}

# --- 🔄 ሰሌዳውን ግሩፕ ላይ Update ማድረግ ---
def update_pinned_board():
    try:
        res = supabase.table("bingo_slots").select("slot_number, is_booked, player_name").order("slot_number").execute()
        board_text = "🎰 **Fasil Bingo (የዕጣ ሰሌዳ)** 🎰\n"
        board_text += f"📅 የታደሰበት፦ {datetime.now().strftime('%H:%M')}\n\n"
        for r in res.data:
            status = f"✅ {r['player_name']}" if r['is_booked'] else "⚪ ክፍት"
            board_text += f"{r['slot_number']}. {status}\n"
        
        msg_id_res = supabase.table("settings").select("value").eq("key", "pinned_msg_id").execute()
        if msg_id_res.data:
            pinned_id = int(msg_id_res.data[0]['value'])
            bot.edit_message_text(board_text[:4000], chat_id=GROUP_ID, message_id=pinned_id, parse_mode="Markdown")
    except Exception as e: print(f"Board Update Error: {e}")

# --- 🛡️ ክፍያ ፍተሻ (Calculate Tickets) ---
def verify_payment_strict(text):
    text = text.upper()
    if any(k in text for k in ['WITHDRAW', 'CASH OUT', 'አውጥተዋል', 'DEBITED']):
        return False, "❌ ይህ የብር መውጫ ደረሰኝ ነው።", None
    
    tid_match = re.search(r'(?:ID|TXN|TRANS|FT|ID:)\s*[:\s]*([A-Z0-9]{6,15})', text)
    if not tid_match: return False, "❌ የደረሰኝ ID አልተገኘም።", None
    tid = tid_match.group(1)

    try:
        used = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
        if used.data: return False, "❌ ይህ ደረሰኝ ቀደም ብሎ ተመዝግቧል።", None
    except: pass

    price = float(supabase.table("settings").select("value").eq("key", "ticket_price").execute().data[0]['value'])
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    amt = float(amounts[0]) if amounts else 0
    
    if amt < price: return False, f"❌ መጠኑ ከ {price} ብር ያነሰ ነው።", None
    
    tickets_count = int(amt // price)
    return True, amt, {"tid": tid, "tickets": tickets_count}

# --- 🛰️ HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = message.from_user.id
    supabase.table("users").upsert({"user_id": str(u_id), "username": message.from_user.username}).execute()
    bot.send_message(message.chat.id, "እንኳን ወደ Fasil Bingo መጡ! 🎰\nክፍያ ፈጽመው SMS እዚህ ይላኩ።")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""

    # --- ADMIN: RESET & BROADCAST ---
    if u_id == ADMIN_ID:
        if txt == "🔄 Reset":
            supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
            supabase.table("used_transactions").delete().neq("tid", "0").execute()
            update_pinned_board()
            bot.send_message(u_id, "🔄 ሰሌዳው ጸድቷል!")
            return
        if txt == "📤 ሰሌዳ ላክ":
            msg = bot.send_message(GROUP_ID, "🎰 ሰሌዳው እየተዘጋጀ ነው...")
            supabase.table("settings").upsert({"key": "pinned_msg_id", "value": str(msg.message_id)}).execute()
            update_pinned_board()
            return

    # --- PAYMENT DETECTION ---
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'birr', 'ያስተላለፉት']):
        valid, amt, data = verify_payment_strict(txt)
        if not valid:
            bot.reply_to(message, amt)
            return
        
        pending_payments[u_id] = {
            "tid": data['tid'], 
            "amt": amt, 
            "tickets": data['tickets'], 
            "total": data['tickets'], 
            "step": "name", 
            "time": time.time()
        }
        bot.reply_to(message, f"✅ ክፍያ ተረጋግጧል! {amt} ብር ({data['tickets']} ዕጣ)።\nአሁን **ሙሉ ስምዎን** ይላኩ።")
        return

    # --- REGISTRATION (Multi-Ticket Logic) ---
    if u_id in pending_payments:
        p = pending_payments[u_id]
        if p["step"] == "name":
            p["name"], p["step"] = txt, "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን {p['tickets']} ቁጥሮችን መምረጥ ይችላሉ። የመጀመሪያውን ቁጥር ይላኩ (1-100)፦")
        elif p["step"] == "num" and txt.isdigit():
            num = int(txt)
            if num < 1 or num > 100:
                bot.reply_to(message, "❌ ከ1-100 ይምረጡ።")
                return
            
            check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            if check.data and check.data[0]['is_booked']:
                bot.reply_to(message, "❌ ቁጥሩ ተይዟል! ሌላ ይምረጡ።")
                return

            # መመዝገብ
            supabase.table("bingo_slots").update({"player_name": p["name"], "is_booked": True}).eq("slot_number", num).execute()
            p["tickets"] -= 1
            update_pinned_board()
            
            if p["tickets"] > 0:
                bot.send_message(u_id, f"✅ ቁጥር {num} ተመዝግቧል! {p['tickets']} ዕጣ ይቀሩዎታል። ቀጣዩን ቁጥር ይላኩ፦")
            else:
                supabase.table("used_transactions").insert({"tid": p["tid"], "user_id": str(u_id), "amount": p["amt"]}).execute()
                bot.send_message(u_id, f"✅ ተሳክቷል! ሁሉንም {p['total']} ቁጥሮች መርጠዋል። መልካም ዕድል!")
                bot.send_message(GROUP_ID, f"🎟 **አዲስ ምዝገባ!**\n👤 ስም፦ {p['name']}\n🔢 {p['total']} ዕጣዎችን መርጠዋል።")
                del pending_payments[u_id]
        return

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Online"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    bot.infinity_polling()
