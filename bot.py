import telebot
from supabase import create_client, Client
import re, time, os, threading, random
from flask import Flask

# --- 1. Flask ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "Bingo Bot Active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- 2. CONFIG ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
GROUP_ID = -1003881429974 
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)

MY_NAMES = ["fasil", "fassil", "andualem"]
MY_CBE, MY_TELEBIRR = "1000584461757", "0951381356"
pending_payments = {}

# --- 3. FUNCTIONS ---

def get_live_leaderboard():
    """ግሩፕ ላይ በቁጥሩ ቦታ ስም ተክቶ የሚያሳይ ሰንጠረዥ"""
    try:
        res = supabase.table("bingo_slots").select("slot_number", "is_booked", "player_name").order("slot_number").execute()
        text = "🎰 **FASIL VIP BINGO LIVE BOARD** 🎰\n\n"
        
        for row in res.data:
            num = row['slot_number']
            if row['is_booked']:
                # ቁጥሩ ከተያዘ ስሙን ያሳያል (ረጅም ከሆነ ያሳጥረዋል)
                name = row['player_name'][:8]
                text += f"📍 {num:02d} - {name} ✅\n"
            else:
                # ካልተያዘ ቁጥሩን ብቻ ያሳያል
                text += f"⬜️ {num:02d} - ክፍት ነው\n"
        
        # ሰንጠረዡ ረጅም ስለሚሆን ለግሩፕ እንዲመች በትንሹ መላክ ይቻላል
        return text
    except: return "⚠️ ቦርዱን ማግኘት አልተቻለም።"

def assign_free_slot(user_name):
    res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).execute()
    if res.data:
        free_nums = [r['slot_number'] for r in res.data]
        selected = random.choice(free_nums)
        supabase.table("bingo_slots").update({"player_name": user_name, "is_booked": True}).eq("slot_number", selected).execute()
        return selected
    return None

# --- 4. HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.chat.id)
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None
    
    try:
        supabase.table("users").upsert({"user_id": user_id, "user_name": message.from_user.first_name, "referred_by": referrer_id}).execute()
    except: pass

    invite_link = f"https://t.me/{(bot.get_me()).username}?start={user_id}"
    bot.reply_to(message, f"ሰላም! የርስዎ መጋበዣ ሊንክ፦\n`{invite_link}`", parse_mode="Markdown")

@bot.message_handler(commands=['viewslot'])
def view(message):
    # ሰንጠረዡን በምስል ወይም በጽሁፍ መላክ (ጽሁፉ ረጅም ከሆነ ቴሌግራም ላይቆርጠው ይችላል)
    bot.reply_to(message, "🎰 ወቅታዊውን የቢንጎ ቦርድ በግሩፑ ላይ ይመልከቱ ወይም እዚህ ይጫኑ፦ /leaderboard")

@bot.message_handler(commands=['leaderboard'])
def show_l_board(message):
    # ይህ በብዛት የገዙትን Top 5 ያሳያል
    res = supabase.table("bingo_slots").select("player_name").eq("is_booked", True).execute()
    counts = {}
    for r in res.data: counts[r['player_name']] = counts.get(r['player_name'], 0) + 1
    sorted_c = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    msg = "🏆 **ከፍተኛ ተጫዋቾች** 🏆\n"
    for name, count in sorted_c: msg += f"👤 {name} — {count} ቁጥሮች\n"
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    user_id = message.chat.id
    text = message.text or ""

    # 1. ክፍያ ማረጋገጥ
    if any(k in text.lower() for k in ['cbe', 'telebirr', 'ብር', 'transferred']):
        bot.reply_to(message, "⏳ እያረጋገጥኩ ነው...")
        tid_match = re.search(r'(?i)(?:id|txn|Ref|FT|DCC|ቁጥር)[:\s]*([A-Z0-9&]+)', text)
        if tid_match:
            tid = tid_match.group(1).upper()
            pending_payments[user_id] = {"tid": tid, "step": "awaiting_name"}
            bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! አሁን በሰንጠረዡ ላይ እንዲሰፍር የሚፈልጉትን **ስም ወይም ስልክ ቁጥር** ይላኩ።")
        return

    # 2. ስም መቀበል
    if user_id in pending_payments and pending_payments[user_id]["step"] == "awaiting_name":
        pending_payments[user_id]["player_name"] = text
        pending_payments[user_id]["step"] = "awaiting_number"
        bot.reply_to(message, f"እሺ **{text}**! አሁን የሚፈልጉትን ቁጥር (1-100) ይላኩ።")
        return

    # 3. ቁጥር መቀበል እና ግሩፕ ላይ መለጠፍ
    if user_id in pending_payments and pending_payments[user_id]["step"] == "awaiting_number" and text.isdigit():
        num = int(text)
        name = pending_payments[user_id]["player_name"]
        
        # በዳታቤዝ መመዝገብ
        supabase.table("bingo_slots").update({"player_name": name, "is_booked": True}).eq("slot_number", num).execute()
        supabase.table("used_transactions").insert({"tid": pending_payments[user_id]["tid"], "user_id": user_id}).execute()
        
        bot.reply_to(message, f"✅ ቁጥር {num} በስምዎ ተመዝግቧል!")
        
        # ግሩፕ ላይ ማስታወቅ (ይህ አንተ የፈለግከው ነው!)
        bot.send_message(GROUP_ID, f"🎰 **አዲስ ተመዝጋቢ!**\n\n👤 ተጫዋች፦ {name}\n🎟 የተያዘ ቁጥር፦ {num}\n\n✅ ቁጥሩ በሰንጠረዡ ላይ ተሰይሟል።")
        
        # ሪፈራል ቦነስ ቼክ
        user_res = supabase.table("users").select("referred_by", "has_played").eq("user_id", str(user_id)).execute()
        if user_res.data and not user_res.data[0]['has_played']:
            ref_id = user_res.data[0]['referred_by']
            if ref_id:
                ref_user = supabase.table("users").select("user_name").eq("user_id", ref_id).execute()
                if ref_user.data:
                    f_num = assign_free_slot(ref_user.data[0]['user_name'])
                    if f_num: bot.send_message(ref_id, f"🎁 ሪፈራል ስጦታ! ቁጥር {f_num} በነፃ ተሰጥቶዎታል።")
            supabase.table("users").update({"has_played": True}).eq("user_id", str(user_id)).execute()
        
        del pending_payments[user_id]

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
