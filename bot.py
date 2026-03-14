import telebot
from supabase import create_client, Client
import re, os
from datetime import datetime

# --- 1. CONFIGURATION (ቁልፎች እዚሁ አሉ) ---
TOKEN = '8721334129:AAGhN-nLB0bs-auvy5M_XPznDn9z4xyFHoI'
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}

# --- 2. FUNCTIONS ---
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
            bot.edit_message_text(board_text[:4000], chat_id=GROUP_ID, message_id=int(msg_id_res.data[0]['value']), parse_mode="Markdown")
    except: pass

def verify_payment(text):
    text = text.upper()
    tid_match = re.search(r'(?:ID|TXN|FT|ID:)\s*[:\s]*([A-Z0-9]{6,15})', text)
    if not tid_match: return False, "❌ የደረሰኝ ID አልተገኘም", None
    tid = tid_match.group(1)
    
    # የዋጋ ስሌት (20 ብር ለአንድ እጣ)
    amounts = re.findall(r'(?:ETB|BIRR|ብር)[:\s]*([\d\.]+)', text)
    amt = float(amounts[0]) if amounts else 0
    if amt < 20: return False, "❌ የላኩት ብር ከ 20 ብር ያነሰ ነው", None
    
    return True, amt, {"tid": tid, "tickets": int(amt // 20)}

# --- 3. HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    try:
        supabase.table("users").upsert({"user_id": str(message.from_user.id), "username": message.from_user.username}).execute()
        bot.reply_to(message, "እንኳን ወደ ፋሲል ቢንጎ በሰላም መጡ! 🎰\nክፍያ ፈጽመው SMS እዚህ ይላኩ።")
    except:
        bot.reply_to(message, "ሰላም! ቦቱ ዝግጁ ነው።")

@bot.message_handler(func=lambda m: True)
def handle(message):
    u_id = message.chat.id
    txt = message.text or ""

    # Admin: ሰሌዳ ለመላክ
    if u_id == ADMIN_ID and txt == "📤 ሰሌዳ ላክ":
        msg = bot.send_message(GROUP_ID, "🎰 ሰሌዳው እየተዘጋጀ ነው...")
        supabase.table("settings").upsert({"key": "pinned_msg_id", "value": str(msg.message_id)}).execute()
        update_pinned_board()
        return

    # የክፍያ SMS
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'birr', 'ያስተላለፉት']):
        valid, amt, data = verify_payment(txt)
        if not valid: return bot.reply_to(message, amt)
        
        pending_payments[u_id] = {"tid": data['tid'], "amt": amt, "tickets": data['tickets'], "total": data['tickets'], "step": "name"}
        bot.reply_to(message, f"✅ {amt} ብር ተረጋግጧል ({data['tickets']} ዕጣ)።\nአሁን ስምዎን ይላኩ።")
        return

    # ምዝገባ
    if u_id in pending_payments:
        p = pending_payments[u_id]
        if p["step"] == "name":
            p["name"], p["step"] = txt, "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን {p['tickets']} ቁጥሮችን ይምረጡ (1-100)።")
        elif p["step"] == "num" and txt.isdigit():
            num = int(txt)
            # ቁጥሩ ክፍት መሆኑን ቼክ ማድረግ
            check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            if check.data and check.data[0]['is_booked']:
                return bot.reply_to(message, "❌ ቁጥሩ ተይዟል!")
            
            supabase.table("bingo_slots").update({"player_name": p["name"], "is_booked": True}).eq("slot_number", num).execute()
            p["tickets"] -= 1
            update_pinned_board()
            
            if p["tickets"] > 0:
                bot.send_message(u_id, f"✅ ቁጥር {num} ተመዝግቧል! {p['tickets']} ቀርቶዎታል።")
            else:
                supabase.table("used_transactions").insert({"tid": p["tid"], "user_id": str(u_id), "amount": p["amt"]}).execute()
                bot.send_message(u_id, "✅ ምዝገባው ተጠናቋል! መልካም ዕድል!")
                bot.send_message(GROUP_ID, f"🎟 አዲስ ምዝገባ፦ {p['name']} ({p['total']} ዕጣ)")
                del pending_payments[u_id]

print("Railway Bot is starting...")
bot.infinity_polling()
