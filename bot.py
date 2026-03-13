import telebot
from supabase import create_client, Client
import re, time, os, threading
from datetime import datetime
from flask import Flask
from telebot import types

# --- 1. CONFIGURATION ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 
SB_URL = "https://hpdhhomunbpcluuhmila.supabase.co"
SB_KEY = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwZGhob211bmJwY2x1dWhtaWxhIiwicm9sZMi6ImFub24iLCJpYXQiOjE3NzMyNDM2MDcsImV4cCI6MjA4ODgxOTYwN30.EIDhhsFaR6Qw5VVobmQs5JYlbJaDBjxWf_F7kM-jEn0"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}
admin_states = {}

# --- 💰 DYNAMIC PRICE GETTER ---
def get_current_price():
    try:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        if res.data:
            return float(res.data[0]['value'])
        return 10.0
    except: return 10.0

# --- 🛡️ STRICT VERIFIER ---
def verify_payment_strict(text):
    text = text.upper()
    now = datetime.now()
    today_date = now.strftime("%d/%m/%Y")
    
    tid_match = re.search(r'(?:ID|TXN|TRANS|FT|NUMBER IS)[:\s]*([A-Z0-9]{6,12})', text)
    if not tid_match: return False, "❌ የግብይት ቁጥር (ID) አልተገኘም።", None, None
    tid = tid_match.group(1)

    try:
        used = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
        if used.data: return False, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል።", None, None
    except: pass

    price = get_current_price()
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    amt = float(amounts[0]) if amounts else 0
    if amt < price: return False, f"❌ መጠኑ ከ {price} ብር ያነሰ ነው።", None, None
    
    if "84461757" not in text and "51381356" not in text:
        return False, "❌ ደረሰኙ ወደ ፋሲል አካውንት አልተላከም።", None, None

    return True, amt, tid, today_date

# --- 🏠 KEYBOARDS ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📖 እንዴት መጫወት ይቻላል?", "📊 ክፍት ቁጥሮችን እይ", "💰 የጨዋታ ዋጋ")
    if user_id == ADMIN_ID: markup.add("⚙️ Admin Panel")
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📊 ሪፖርት", "💰 ዋጋ ቀይር", "🔄 Reset", "🏠 ወደ ዋና ሜኑ")
    return markup

# --- 🛰️ HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = message.from_user.id
    admin_states[u_id] = None
    price = get_current_price()
    welcome = (f"ሰላም {message.from_user.first_name}! 🎰 Fasil Bingo\n\n"
              f"🏦 **CBE:** `1000584461757`\n"
              f"📱 **Telebirr:** `0951381356`\n"
              f"💵 **የአሁኑ ዋጋ:** `{price} ብር`\n\n"
              "👉 ለመመዝገብ ደረሰኙን (SMS) እዚህ **Forward** ያድርጉ።")
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu(u_id), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⚙️ Admin Panel" and message.from_user.id == ADMIN_ID)
def admin_panel(message):
    admin_states[ADMIN_ID] = None
    bot.send_message(ADMIN_ID, "እንኳን ደህና መጡ አድሚን ፋሲል!", reply_markup=admin_menu())

# --- 🎰 PROCESS LOGIC ---
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""

    # 1. 📖 እንዴት መጫወት ይቻላል?
    if txt == "📖 እንዴት መጫወት ይቻላል?":
        instruction = (
            "📖 **የአጠቃቀም መመሪያ**\n\n"
            "1️⃣ መጀመሪያ ወደ CBE ወይም Telebirr ብር ይላኩ።\n"
            "2️⃣ የደረሰኙን መልዕክት (SMS) ሙሉ በሙሉ ኮፒ አድርገው እዚህ ይላኩ።\n"
            "3️⃣ ቦቱ ደረሰኙን ሲያረጋግጥ ስምዎን ይጠይቅዎታል።\n"
            "4️⃣ በመጨረሻም ከ1-100 ያሉ ክፍት ቁጥሮችን መርጠው ይላኩ።\n\n"
            "መልካም ዕድል! 🎰"
        )
        bot.send_message(u_id, instruction, parse_mode="Markdown")
        return

    # 2. 📊 ሪፖርት (ለአድሚን ብቻ)
    if txt == "📊 ሪፖርት" and message.from_user.id == ADMIN_ID:
        try:
            res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", True).execute()
            count = len(res.data) if res.data else 0
            price = get_current_price()
            if count == 0:
                bot.send_message(ADMIN_ID, "📊 **የዛሬ ሪፖርት**\n\nእስካሁን ምንም የተመዘገበ ተጫዋች የለም።")
            else:
                bot.send_message(ADMIN_ID, f"📊 **የዛሬ ሪፖርት**\n\n🎟 የተያዙ ቁጥሮች፦ {count}\n💰 አጠቃላይ ብር፦ {count * price} ብር")
        except:
            bot.send_message(ADMIN_ID, "❌ ሪፖርት ማምጣት አልተሳካም።")
        return

    # 3. 🔄 Reset (ለአድሚን ብቻ)
    if txt == "🔄 Reset" and message.from_user.id == ADMIN_ID:
        try:
            supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
            supabase.table("used_transactions").delete().neq("tid", "0").execute()
            bot.send_message(ADMIN_ID, "🔄 ሁሉም ቁጥሮች እና ደረሰኞች ጸድተዋል። አዲስ ዙር ተጀምሯል!", reply_markup=admin_menu())
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ Reset አልተሳካም፦ {str(e)}")
        return

    # 4. 💰 ዋጋ ቀይር (ለአድሚን ብቻ)
    if txt == "💰 ዋጋ ቀይር" and message.from_user.id == ADMIN_ID:
        admin_states[ADMIN_ID] = "waiting_for_price"
        bot.send_message(ADMIN_ID, "እባክዎ አዲሱን ዋጋ በቁጥር ብቻ ያስገቡ (ለምሳሌ፦ 50)።")
        return

    if admin_states.get(u_id) == "waiting_for_price":
        if txt.isdigit():
            try:
                check = supabase.table("settings").select("*").eq("key", "ticket_price").execute()
                if check.data:
                    supabase.table("settings").update({"value": str(txt)}).eq("key", "ticket_price").execute()
                else:
                    supabase.table("settings").insert({"key": "ticket_price", "value": str(txt)}).execute()
                bot.send_message(u_id, f"✅ የቢንጎ ዋጋ ወደ {txt} ብር ተቀይሯል።", reply_markup=admin_menu())
                admin_states[u_id] = None
            except Exception as e:
                bot.send_message(u_id, f"❌ ዳታቤዝ ላይ መመዝገብ አልተቻለም፦ {str(e)}")
        else:
            bot.send_message(u_id, "❌ እባክዎ ቁጥር ብቻ ያስገቡ።")
        return

    # 5. የቤት መመለሻ
    if txt == "🏠 ወደ ዋና ሜኑ":
        admin_states[u_id] = None
        bot.send_message(u_id, "ወደ ዋና ሜኑ ተመልሰናል", reply_markup=main_menu(u_id))
        return

    # 6. የደረሰኝ ፍተሻ
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'ብር', 'dear', 'successfully']):
        is_valid, amt_or_reason, tid, r_date = verify_payment_strict(txt)
        if not is_valid:
            bot.reply_to(message, amt_or_reason)
            return
        pending_payments[u_id] = {"tid": tid, "amt": amt_or_reason, "date": r_date, "step": "name"}
        bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! አሁን ስምዎን ይላኩ።")
        return

    # 7. ምዝገባ መቀጠያ (ስም እና ቁጥር)
    if u_id in pending_payments:
        p_data = pending_payments[u_id]
        if p_data["step"] == "name":
            p_data["name"] = txt
            p_data["step"] = "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን ቁጥር ይምረጡ (1-100)።")
        elif p_data["step"] == "num" and txt.isdigit():
            num = int(txt)
            try:
                check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check.data and check.data[0]['is_booked']:
                    bot.reply_to(message, "❌ ቁጥሩ ተይዟል! ሌላ ይምረጡ።")
                    return
                supabase.table("bingo_slots").update({"player_name": p_data["name"], "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": p_data["tid"], "user_id": str(u_id), "amount": p_data["amt"]}).execute()
                bot.send_message(u_id, f"✅ ቁጥር {num} ተመዝግቧል!", reply_markup=main_menu(u_id))
                bot.send_message(GROUP_ID, f"🎰 አዲስ ተመዝጋቢ፦ {p_data['name']} (ቁጥር {num})")
                del pending_payments[u_id]
            except Exception as e: 
                bot.reply_to(message, f"❌ ስህተት፦ {str(e)}")
        return

    # 8. ሌሎች በተኖች
    if txt == "💰 የጨዋታ ዋጋ":
        bot.reply_to(message, f"💰 ወቅታዊ ዋጋ፦ {get_current_price()} ብር")
        
    if txt == "📊 ክፍት ቁጥሮችን እይ":
        try:
            res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", False).order("slot_number").execute()
            slots = [str(s['slot_number']) for s in res.data]
            bot.send_message(u_id, "📊 **ክፍት ቁጥሮች፦**\n\n" + ", ".join(slots))
        except: bot.reply_to(message, "❌ መረጃ ማምጣት አልተቻለም።")

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    bot.infinity_polling()
