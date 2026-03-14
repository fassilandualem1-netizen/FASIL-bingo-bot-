import telebot
from supabase import create_client, Client
from flask import Flask
from threading import Thread
import time, re, os
from datetime import datetime

# --- 1. CONFIGURATION ---
# አዲሱ Token እና የSupabase መረጃዎች
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

# ማንነቶች (እንደ አስፈላጊነቱ ቀይራቸው)
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
app = Flask('')

# ተጠቃሚዎች መረጃ እስከሚጨርሱ ለጊዜው የሚያዝበት
user_state = {}

# --- 2. UPTIMEROBOT / KEEP-ALIVE (FLASK) ---
@app.route('/')
def home():
    return "Fasil Bingo Bot is running and awake!"

def run_flask():
    # Render የሚሰጠውን PORT በራሱ ያነባል
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- 3. SMS VERIFICATION (GASHA METHOD) ---
def verify_gasha_sms(text):
    text = text.upper()
    # የጋሻ ቤት መለያ ቁልፍ ቃላት (G-Money, ID, Amt)
    tid_match = re.search(r'(?:ID|TXN|G-|FT)[:\s]*([A-Z0-9]{6,16})', text)
    amt_match = re.search(r'(?:BIRR|ETB|ብር|AMT)[:\s]*([\d\.]+)', text)
    
    if tid_match and amt_match:
        return tid_match.group(1), float(amt_match.group(1))
    return None, None

# --- 4. BOARD UPDATER ---
def update_pinned_board():
    try:
        res = supabase.table("bingo_slots").select("slot_number, is_booked, player_name").order("slot_number").execute()
        if not res.data: return
        
        board_text = "🎰 **Fasil Bingo - የዕጣ ሰሌዳ** 🎰\n"
        board_text += f"🕒 የታደሰበት፦ {datetime.now().strftime('%H:%M')}\n\n"
        
        for r in res.data:
            status = f"✅ {r['player_name']}" if r['is_booked'] else "⚪ ክፍት"
            board_text += f"{r['slot_number']}. {status}\n"
        
        # የተቀመጠውን መልዕክት ማደስ
        msg_id_res = supabase.table("settings").select("value").eq("key", "pinned_msg_id").execute()
        if msg_id_res.data:
            bot.edit_message_text(board_text[:4000], chat_id=GROUP_ID, message_id=int(msg_id_res.data[0]['value']), parse_mode="Markdown")
    except Exception as e:
        print(f"Board update error: {e}")

# --- 5. BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    try:
        supabase.table("users").upsert({"user_id": str(message.from_user.id), "username": message.from_user.username}).execute()
        bot.reply_to(message, "እንኳን ወደ ፋሲል ቢንጎ በሰላም መጡ! 🎰\n\nለመሳተፍ የጋሻ ቤት (Gasha) ወይም የባንክ ክፍያ SMS እዚህ ይላኩ።")
    except:
        bot.reply_to(message, "ሰላም! ቦቱ ዝግጁ ነው።")

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    u_id = message.chat.id
    txt = message.text

    # Admin: ሰሌዳ ለመላክ
    if u_id == ADMIN_ID and txt == "📤 ሰሌዳ ላክ":
        msg = bot.send_message(GROUP_ID, "🎰 ሰሌዳው እየተዘጋጀ ነው...")
        supabase.table("settings").upsert({"key": "pinned_msg_id", "value": str(msg.message_id)}).execute()
        update_pinned_board()
        return

    # የክፍያ SMS ከሆነ (Gasha/Bank)
    tid, amt = verify_gasha_sms(txt)
    if tid:
        # TID ቀደም ብሎ ጥቅም ላይ መዋሉን ቼክ ማድረግ
        check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
        if check.data:
            return bot.reply_to(message, "❌ ይህ የደረሰኝ ቁጥር ቀደም ብሎ ጥቅም ላይ ውሏል!")
        
        if amt >= 20:
            tickets = int(amt // 20)
            user_state[u_id] = {"tid": tid, "amt": amt, "tickets": tickets, "step": "get_name"}
            bot.reply_to(message, f"✅ የ {amt} ብር ክፍያ ተረጋግጧል! ({tickets} ዕጣ)\n\nእባክዎ ስምዎን ይላኩ።")
        else:
            bot.reply_to(message, "❌ ዝቅተኛው የክፍያ መጠን 20 ብር ነው።")
        return

    # የምዝገባ ሂደት (ስም እና ቁጥር መቀበል)
    if u_id in user_state:
        state = user_state[u_id]
        
        if state["step"] == "get_name":
            state["name"] = txt
            state["step"] = "get_number"
            bot.reply_to(message, f"እሺ {txt}! አሁን ከ 1-100 ያሉትን {state['tickets']} ቁጥሮች ይምረጡ። (አንድ በአንድ ይላኩ)")
            
        elif state["step"] == "get_number" and txt.isdigit():
            num = int(txt)
            if not (1 <= num <= 100):
                return bot.reply_to(message, "❌ እባክዎ ከ 1 እስከ 100 ያለ ቁጥር ይምረጡ።")
            
            # ቁጥሩ መያዙን ቼክ ማድረግ
            check_slot = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            if check_slot.data and check_slot.data[0]['is_booked']:
                return bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል! ሌላ ይምረጡ።")
            
            # ቁጥሩን መመዝገብ
            supabase.table("bingo_slots").update({"player_name": state["name"], "is_booked": True}).eq("slot_number", num).execute()
            state["tickets"] -= 1
            update_pinned_board()
            
            if state["tickets"] > 0:
                bot.reply_to(message, f"✅ ቁጥር {num} ተመዝግቧል! {state['tickets']} ዕጣ ቀርቶዎታል። ቀጣይ ቁጥር ይላኩ።")
            else:
                # ምዝገባ ተጠናቀቀ - TID መዝግብ
                supabase.table("used_transactions").insert({"tid": state["tid"], "user_id": str(u_id), "amount": state["amt"]}).execute()
                bot.send_message(u_id, "✅ ምዝገባዎ ሙሉ በሙሉ ተጠናቋል! መልካም ዕድል!")
                bot.send_message(GROUP_ID, f"🎟 አዲስ ተጫዋች፦ {state['name']} ገብቷል!")
                del user_state[u_id]

# --- 6. START BOT ---
if __name__ == "__main__":
    keep_alive() # ለ UptimeRobot
    print("Fasil Bingo Bot is starting...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
