import telebot
from supabase import create_client, Client
import re, time, threading, requests
from flask import Flask
from telebot import types
from datetime import datetime

# --- 1. CONFIGURATION ---
API_TOKEN = '8721334129:AAGmSeFapCG6pg2GcOvmhTphIRTCjx_rU-E'
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"
RENDER_URL = "https://fasil-bingo-bot-assistant.onrender.com"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}

# --- 🔄 ሰሌዳውን ግሩፕ ላይ Update የማድረጊያ ተግባር ---
def update_pinned_board():
    try:
        res = supabase.table("bingo_slots").select("slot_number, is_booked, player_name").order("slot_number").execute()
        board_text = "🎰 **Fasil Bingo (የዕጣ ሰሌዳ)** 🎰\n"
        board_text += f"📅 የታደሰበት ሰዓት፦ {datetime.now().strftime('%H:%M')}\n\n"
        for r in res.data:
            status = f"✅ {r['player_name']}" if r['is_booked'] else "⚪ ክፍት"
            board_text += f"{r['slot_number']}. {status}\n"
        
        msg_id_res = supabase.table("settings").select("value").eq("key", "pinned_msg_id").execute()
        if msg_id_res.data:
            pinned_id = int(msg_id_res.data[0]['value'])
            bot.edit_message_text(board_text[:4000], chat_id=GROUP_ID, message_id=pinned_id, parse_mode="Markdown")
    except Exception as e:
        print(f"Board Update Error: {e}")

# --- 🛡️ ክፍያ ፍተሻ (Wallet Calculation) ---
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

    try:
        price_res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        price = float(price_res.data[0]['value']) if price_res.data else 20.0
    except: price = 20.0

    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    amt = float(amounts[0]) if amounts else 0
    if amt < price: return False, f"❌ የላኩት ብር ከአንድ ዕጣ ዋጋ ({price} ብር) ያነሰ ነው።", None

    tickets_count = int(amt // price)
    return True, amt, {"tid": tid, "tickets": tickets_count}

# --- 🛰️ HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = str(message.from_user.id)
    try:
        supabase.table("users").upsert({"user_id": u_id, "username": message.from_user.username}).execute()
        bot.send_message(message.chat.id, "ሰላም! እንኳን ወደ ፋሲል ቢንጎ በሰላም መጡ። 🎰\nክፍያ ፈጽመው SMS እዚህ ይላኩ።")
    except Exception as e:
        bot.send_message(message.chat.id, "ሰላም! ቦቱ ንቁ ነው (የዳታቤዝ ግንኙነት በመሞከር ላይ)።")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""

    if u_id == ADMIN_ID:
        if txt == "🔄 Reset":
            supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
            supabase.table("used_transactions").delete().neq("tid", "0").execute()
            update_pinned_board()
            bot.reply_to(message, "🔄 ሁሉም መረጃዎች ተሰርዘዋል።")
            return
        if txt == "📤 ሰሌዳ ላክ":
            msg = bot.send_message(GROUP_ID, "🎰 ሰሌዳው እየተዘጋጀ ነው...")
            supabase.table("settings").upsert({"key": "pinned_msg_id", "value": str(msg.message_id)}).execute()
            update_pinned_board()
            return

    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'birr', 'ያስተላለፉት']):
        valid, amt, data = verify_payment_strict(txt)
        if not valid:
            bot.reply_to(message, amt)
            return
        
        pending_payments[u_id] = {
            "tid": data['tid'], "amt": amt, "tickets": data['tickets'], 
            "total": data['tickets'], "step": "name", "time": time.time()
        }
        bot.reply_to(message, f"✅ ክፍያ ተረጋግጧል! {amt} ብር ({data['tickets']} ዕጣ)።\nአሁን **ሙሉ ስምዎን** ይላኩ።")
        return

    if u_id in pending_payments:
        p = pending_payments[u_id]
        if p["step"] == "name":
            p["name"], p["step"] = txt, "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን {p['tickets']} ቁጥሮችን መምረጥ ይችላሉ። ቁጥር ይላኩ (1-100)፦")
        elif p["step"] == "num" and txt.isdigit():
            num = int(txt)
            check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            if check.data and check.data[0]['is_booked']:
                bot.reply_to(message, "❌ ቁጥሩ ተይዟል! ሌላ ይምረጡ።")
                return
            supabase.table("bingo_slots").update({"player_name": p["name"], "is_booked": True}).eq("slot_number", num).execute()
            p["tickets"] -= 1
            update_pinned_board()
            if p["tickets"] > 0:
                bot.send_message(u_id, f"✅ ቁጥር {num} ተመዝግቧል! {p['tickets']} ዕጣ ይቀሩዎታል። ቀጣዩን ቁጥር ይላኩ፦")
            else:
                supabase.table("used_transactions").insert({"tid": p["tid"], "user_id": str(u_id), "amount": p["amt"]}).execute()
                bot.send_message(u_id, "✅ ተሳክቷል! ሁሉንም ዕጣዎች መርጠው ጨርሰዋል። መልካም ዕድል!")
                bot.send_message(GROUP_ID, f"🎟 **አዲስ ምዝገባ!**\n👤 ስም፦ {p['name']}\n🔢 {p['total']} ዕጣዎችን መርጠዋል።")
                del pending_payments[u_id]
        return

# --- 🛰️ KEEP ALIVE (SELF-PING) ---
def self_ping():
    while True:
        try:
            requests.get(RENDER_URL)
            print("🚀 Self-ping successful")
        except:
            print("❌ Self-ping failed")
        time.sleep(600) # በየ 10 ደቂቃው

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    threading.Thread(target=self_ping, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    print("🚀 ቦቱ ስራ ጀምሯል...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
