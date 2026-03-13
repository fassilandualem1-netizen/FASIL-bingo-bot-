import telebot
from supabase import create_client, Client
import re, time, os, threading, random
from flask import Flask

app = Flask(__name__)
@app.route('/')
def health_check(): return "Bingo Bot Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# CONFIG
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
GROUP_ID = -1003881429974 
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}

def extract_tid(text):
    # CBE FT... ቁጥሮችን ጨምሮ ሁሉንም የትራንዛክሽን መለያዎች ይፈልጋል
    match = re.search(r'(?:FT|DCC|TXN|ID|Ref|ቁጥር)[:\s]*([A-Z0-9&]+)', text, re.IGNORECASE)
    return match.group(1).upper() if match else None

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    args = message.text.split()
    ref_id = args[1] if len(args) > 1 else None
    try:
        supabase.table("users").upsert({"user_id": user_id, "user_name": message.from_user.first_name, "referred_by": ref_id}).execute()
    except: pass
    
    bot.reply_to(message, f"ሰላም {message.from_user.first_name}! 🎰\nለመመዝገብ የባንክ መልዕክቱን እዚህ Forward ያድርጉ።\n\n🔗 የእርስዎ መጋበዣ ሊንክ፦\nhttps://t.me/{(bot.get_me()).username}?start={user_id}")

@bot.message_handler(func=lambda message: True)
def handle_msg(message):
    u_id = message.chat.id
    txt = message.text or ""

    # 1. ክፍያ ማረጋገጥ
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'transferred', 'credited', 'birr', 'ብር']):
        tid = extract_tid(txt)
        if tid:
            check = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
            if check.data:
                bot.reply_to(message, "❌ ይህ ማጣቀሻ ቁጥር ቀደም ብሎ ጥቅም ላይ ውሏል!")
            else:
                pending_payments[u_id] = {"tid": tid, "step": "name"}
                bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! በቦርዱ ላይ እንዲሰፍር የሚፈልጉትን **ስም ወይም ስልክ** ይላኩ።")
        else:
            bot.reply_to(message, "❌ የማጣቀሻ ቁጥሩን (TID) ማግኘት አልቻልኩም። እባክዎ ሙሉውን SMS ይላኩ።")
        return

    # 2. ስም መቀበል
    if u_id in pending_payments and pending_payments[u_id]["step"] == "name":
        pending_payments[u_id]["name"] = txt
        pending_payments[u_id]["step"] = "number"
        bot.reply_to(message, f"እሺ {txt}! አሁን ከ 1-100 የሚፈልጉትን ክፍት ቁጥር ይላኩ።")
        return

    # 3. ቁጥር መቀበል
    if u_id in pending_payments and pending_payments[u_id]["step"] == "number" and txt.isdigit():
        num = int(txt)
        if 1 <= num <= 100:
            slot_check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
            if slot_check.data and slot_check.data[0]['is_booked']:
                bot.reply_to(message, f"❌ ቁጥር {num} ተይዟል፣ ሌላ ይምረጡ።")
            else:
                name = pending_payments[u_id]["name"]
                tid = pending_payments[u_id]["tid"]
                
                # ምዝገባ
                supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": tid, "user_id": str(u_id)}).execute()
                
                bot.reply_to(message, f"✅ ቁጥር {num} በስምዎ ተመዝግቧል! መልካም እድል!")
                
                # ግሩፕ ላይ መለጠፍ (Leaderboard style)
                bot.send_message(GROUP_ID, f"🎰 **አዲስ ተመዝጋቢ!**\n\n👤 ተጫዋች፦ {name}\n🎟 የተያዘ ቁጥር፦ {num}\n\n✅ ቁጥሩ በሰንጠረዡ ላይ ተሰይሟል።")
                
                # የሪፈራል ቦነስ ቼክ
                user_res = supabase.table("users").select("referred_by", "has_played").eq("user_id", str(u_id)).execute()
                if user_res.data and not user_res.data[0]['has_played']:
                    ref_id = user_res.data[0]['referred_by']
                    if ref_id:
                        # ጋባዡ 1 ነፃ ቁጥር ያገኛል
                        res_free = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).execute()
                        if res_free.data:
                            free_num = random.choice([r['slot_number'] for r in res_free.data])
                            ref_info = supabase.table("users").select("user_name").eq("user_id", ref_id).execute()
                            ref_name = ref_info.data[0]['user_name'] if ref_info.data else "ጋባዥ"
                            supabase.table("bingo_slots").update({"player_name": f"{ref_name} (Bonus)", "is_booked": True}).eq("slot_number", free_num).execute()
                            bot.send_message(ref_id, f"🎁 **የሪፈራል ስጦታ!**\nየጋበዙት ሰው ስለተጫወተ ቁጥር {free_num} በነፃ ተሰጥቶዎታል።")
                    supabase.table("users").update({"has_played": True}).eq("user_id", str(u_id)).execute()
                
                del pending_payments[u_id]
        else:
            bot.reply_to(message, "❌ እባክዎ ከ 1-100 ያለ ቁጥር ብቻ ይላኩ።")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
