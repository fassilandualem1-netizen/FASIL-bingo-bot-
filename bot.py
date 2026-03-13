import telebot
from supabase import create_client, Client
import re, time, os, threading
from datetime import datetime
from flask import Flask
from telebot import types

# --- 1. CONFIGURATION (አዲሱ መረጃ እዚህ ገብቷል) ---
API_TOKEN = '8721334129:AAHcpUwIywYh_glndRiWWLNryx2CvrjMUFQ'
ADMIN_ID = 8488592165 
GROUP_ID = -1003881429974 
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
pending_payments = {}
admin_states = {}

# --- 💰 DYNAMIC PRICE GETTER ---
def get_current_price():
    try:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        return float(res.data[0]['value']) if res.data else 10.0
    except: return 10.0

# --- 🛡️ VERIFIER ---
def verify_payment_strict(text):
    text = text.upper()
    tid_match = re.search(r'(?:ID|TXN|TRANS|FT|NUMBER IS)[:\s]*([A-Z0-9]{6,12})', text)
    if not tid_match: return False, "❌ የግብይት ቁጥር (ID) አልተገኘም።", None
    tid = tid_match.group(1)

    try:
        used = supabase.table("used_transactions").select("tid").eq("tid", tid).execute()
        if used.data: return False, "❌ ይህ ደረሰኝ ቀደም ብሎ ጥቅም ላይ ውሏል።", None
    except: pass

    price = get_current_price()
    amounts = re.findall(r'(?:ETB|BIRR|ብር|AMT)[:\s]*([\d\.]+)', text)
    amt = float(amounts[0]) if amounts else 0
    if amt < price: return False, f"❌ መጠኑ ከ {price} ብር ያነሰ ነው።", None
    
    return True, amt, tid

# --- 🏠 KEYBOARDS ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("📊 የቢንጎ ሰሌዳ እይ", "💰 የጨዋታ ዋጋ")
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
    bot.send_message(message.chat.id, (
        f"ሰላም {message.from_user.first_name}! 🎰 Fasil Bingo\n\n"
        f"🏦 **CBE:** `1000584461757`\n"
        f"📱 **Telebirr:** `0951381356`\n"
        f"💵 **የአሁኑ ዋጋ:** `{price} ብር`"
    ), reply_markup=main_menu(u_id), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    u_id = message.chat.id
    txt = message.text or ""

    # 1. 📊 የቢንጎ ሰሌዳ (1-100)
    if txt == "📊 የቢንጎ ሰሌዳ እይ":
        try:
            res = supabase.table("bingo_slots").select("slot_number, is_booked, player_name").order("slot_number").execute()
            board = "🎰 **የቢንጎ ሰሌዳ (1-100)**\n\n"
            for r in res.data:
                icon = f"✅ {r['player_name']}" if r['is_booked'] else "⚪ [ክፍት]"
                board += f"{r['slot_number']}. {icon}\n"
            
            if len(board) > 4000:
                bot.send_message(u_id, board[:4000], parse_mode="Markdown")
                bot.send_message(u_id, board[4000:], parse_mode="Markdown")
            else:
                bot.send_message(u_id, board, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ ስህተት፦ {str(e)}")
        return

    # 2. ⚙️ Admin Panel & Actions
    if txt == "⚙️ Admin Panel" and u_id == ADMIN_ID:
        bot.send_message(u_id, "የአድሚን መቆጣጠሪያ", reply_markup=admin_menu())
        return

    if txt == "💰 ዋጋ ቀይር" and u_id == ADMIN_ID:
        admin_states[u_id] = "waiting_for_price"
        bot.send_message(u_id, "እባክዎ አዲሱን ዋጋ በቁጥር ብቻ ያስገቡ (ለምሳሌ፦ 20)።")
        return

    if admin_states.get(u_id) == "waiting_for_price":
        if txt.isdigit():
            try:
                supabase.table("settings").upsert({"key": "ticket_price", "value": str(txt)}).execute()
                bot.send_message(u_id, f"✅ ዋጋው ወደ {txt} ብር ተቀይሯል።", reply_markup=admin_menu())
                admin_states[u_id] = None
            except Exception as e: bot.send_message(u_id, f"❌ ስህተት፦ {str(e)}")
        else: bot.send_message(u_id, "❌ እባክዎ ቁጥር ብቻ ያስገቡ።")
        return

    if txt == "🔄 Reset" and u_id == ADMIN_ID:
        try:
            supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
            supabase.table("used_transactions").delete().neq("tid", "0").execute()
            bot.send_message(u_id, "🔄 ሰሌዳውና ደረሰኞች ጸድተዋል።", reply_markup=admin_menu())
        except Exception as e: bot.reply_to(message, f"❌ ስህተት፦ {str(e)}")
        return

    if txt == "📊 ሪፖርት" and u_id == ADMIN_ID:
        try:
            res = supabase.table("bingo_slots").select("slot_number").eq("is_booked", True).execute()
            count = len(res.data) if res.data else 0
            price = get_current_price()
            msg = f"📊 **ሪፖርት**\n\n🎟 የተያዙ፦ {count}\n💰 ብር፦ {count * price} ብር" if count > 0 else "📊 እስካሁን ምንም ተመዝጋቢ የለም።"
            bot.send_message(u_id, msg)
        except: bot.send_message(u_id, "❌ ሪፖርት ማምጣት አልተሳካም።")
        return

    # 3. ደረሰኝ ፍተሻ
    if any(k in txt.lower() for k in ['cbe', 'telebirr', 'ብር', 'dear', 'successfully']):
        valid, result, tid = verify_payment_strict(txt)
        if not valid:
            bot.reply_to(message, result)
            return
        pending_payments[u_id] = {"tid": tid, "amt": result, "step": "name"}
        bot.reply_to(message, "✅ ክፍያ ተረጋግጧል! አሁን ስምዎን ይላኩ።")
        return

    # 4. ምዝገባ መቀጠያ
    if u_id in pending_payments:
        p = pending_payments[u_id]
        if p["step"] == "name":
            p["name"], p["step"] = txt, "num"
            bot.reply_to(message, f"እሺ {txt}! አሁን ቁጥር ይምረጡ (1-100)።")
        elif p["step"] == "num" and txt.isdigit():
            num = int(txt)
            try:
                check = supabase.table("bingo_slots").select("is_booked").eq("slot_number", num).execute()
                if check.data and check.data[0]['is_booked']:
                    bot.reply_to(message, "❌ ቁጥሩ ተይዟል! ሌላ ይምረጡ።")
                    return
                supabase.table("bingo_slots").update({"player_name": p["name"], "is_booked": True}).eq("slot_number", num).execute()
                supabase.table("used_transactions").insert({"tid": p["tid"], "user_id": str(u_id), "amount": p["amt"]}).execute()
                bot.send_message(u_id, f"✅ ቁጥር {num} ተመዝግቧል!", reply_markup=main_menu(u_id))
                bot.send_message(GROUP_ID, f"🎰 አዲስ ተመዝጋቢ፦ {p['name']} (ቁጥር {num})")
                del pending_payments[u_id]
            except Exception as e: bot.reply_to(message, f"❌ ስህተት፦ {str(e)}")
        return

    if txt == "💰 የጨዋታ ዋጋ": bot.reply_to(message, f"💰 ዋጋ፦ {get_current_price()} ብር")
    if txt == "🏠 ወደ ዋና ሜኑ": bot.send_message(u_id, "ወደ ዋና ሜኑ ተመልሰናል", reply_markup=main_menu(u_id))

app = Flask(__name__)
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
    bot.infinity_polling()
