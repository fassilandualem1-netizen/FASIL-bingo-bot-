import telebot
from flask import Flask, request
from supabase import create_client, Client
import re, time, threading, requests, os
from datetime import datetime

# --- 1. መቆጣጠሪያ ቁልፎች (SETTINGS) ---
TOKEN = '8721334129:AAGhN-nLB0bs-auvy5M_XPznDn9z4xyFHoI'
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"
RENDER_URL = "https://fasil-bingo-bot-assistant.onrender.com"

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
app = Flask(__name__)
pending_payments = {}

# --- 2. WEBHOOK & UPTIME LOGIC (እንዳይቆም የሚያደርገው) ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        return "Forbidden", 403

@app.route("/")
def webhook():
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=RENDER_URL + '/' + TOKEN)
    return "Fasil Bingo Bot is Live and Secure! ✅", 200

# --- 3. የቢንጎ ሰሌዳ ማደሻ ---
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
    except Exception as e: print(f"Board Update Error: {e}")

# --- 4. የክፍያ ማረጋገጫ ---
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
    price = 20.0
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    amt = float(amounts[0]) if amounts else 0
    if amt < price: return False, f"❌ የላኩት ብር ከአንድ ዕጣ ዋጋ ({price} ብር) ያነሰ ነው።", None
    return True, amt, {"tid": tid, "tickets": int(amt // price)}

# --- 5. መልዕክት ተቀባዮች (HANDLERS) ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = str(message.from_user.id)
    try:
        supabase.table("users").upsert({"user_id": u_id, "username": message.from_user.username}).execute()
        bot.send_message(message.chat.id, "ሰላም ፋሲል! ቦቱ በትክክል ተስተካክሏል። 🎰\nክፍያ ፈጽመው SMS እዚህ ይላኩ።")
    except:
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
            bot.reply_to(message, "🔄 ሲስተሙ ጸድቷል!")
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
        pending_payments[u_id] = {"tid": data['tid'], "amt": amt, "tickets": data['tickets'], "total": data['tickets'], "step": "name"}
        bot.reply_to(message, f"✅ ክፍያ ተረጋግጧል! {amt} ብር ({data['tickets']} ዕጣ)።\nአሁን **ሙሉ ስምዎን** ይላኩ።")
        return

    if u_id in pending_payments:
        p = pending_payments[u_id]
        if p["step"] == "name":
            p["name"], p["step"] = txt, "num"
            bot.reply_to(message, f"እሺ {p['name']}! አሁን {p['tickets']} ቁጥሮችን መምረጥ ይችላሉ። ቁጥር ይላኩ (1-100)፦")
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
                bot.send_message(u_id, f"✅ ቁጥር {num} ተመዝግቧል! {p['tickets']} ዕጣ ይቀሩዎታል።")
            else:
                supabase.table("used_transactions").insert({"tid": p["tid"], "user_id": str(u_id), "amount": p["amt"]}).execute()
                bot.send_message(u_id, "✅ ተሳክቷል! መልካም ዕድል!")
                bot.send_message(GROUP_ID, f"🎟 **አዲስ ምዝገባ!**\n👤 ስም፦ {p['name']}\n🔢 {p['total']} ዕጣዎችን መርጠዋል።")
                del pending_payments[u_id]

# --- 6. ቀጣይነትን ማረጋገጫ (SELF-PING) ---
def keep_alive():
    while True:
        try: requests.get(RENDER_URL)
        except: pass
        time.sleep(600) # በየ 10 ደቂቃው

if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    # Webhook-ን በራስ-ሰር እንዲያገናኝ 5 ሰከንድ ይጠብቃል
    threading.Timer(5, lambda: requests.get(RENDER_URL)).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
