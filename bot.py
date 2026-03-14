import telebot
from telebot import types
from supabase import create_client, Client
from flask import Flask
from threading import Thread
import os

# --- 1. CONFIGURATION ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
ADMIN_ID = 8488592165

# --- 2. WEB SERVER FOR RENDER (KEEP ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "Fasil Bingo Bot is Running!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): Thread(target=run_flask).start()

# --- 3. DATABASE HELPER ---
def get_price():
    try:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        return res.data[0]['value'] if res.data else "20"
    except: return "20"

# --- 4. START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = message.from_user.id
    price = get_price()
    
    # የጋራ መረጃ (ለአድሚንም ለተጠቃሚም የሚታይ)
    welcome_text = (
        f"🎰 **እንኳን ወደ ፋሲል ቢንጎ በሰላም መጡ!**\n\n"
        f"🎟 የአሁኑ የዕጣ ዋጋ፦ **{price} ብር**\n"
        f"🏦 **CBE:** `1000XXXXXXXX` \n"
        f"📲 **Telebirr:** `09XXXXXXXX` \n\n"
        "⚠️ ለመሳተፍ የባንክ ደረሰኝ (SMS) እዚህ ይላኩ።"
    )

    if u_id == ADMIN_ID:
        # ለአድሚን (ለአንተ) የሚመጣው ተጨማሪ ፓነል
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔄 Reset Board", "💰 Set Price")
        bot.send_message(u_id, f"🌟 **ሰላም ፋሲል (አድሚን)**\n\n{welcome_text}", reply_markup=markup, parse_mode="Markdown")
    else:
        # ለተራ ተጠቃሚ
        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

# --- 5. ADMIN TOOLS ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def admin_tools(message):
    if message.text == "🔄 Reset Board":
        try:
            supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
            bot.reply_to(message, "✅ የቢንጎ ሰሌዳው በሙሉ ጸድቷል!")
        except Exception as e:
            bot.reply_to(message, f"❌ ስህተት፦ {str(e)}")
            
    elif message.text == "💰 Set Price":
        sent = bot.reply_to(message, "አዲሱን የዕጣ ዋጋ በቁጥር ብቻ ይላኩ (ለምሳሌ፦ 15)፦")
        bot.register_next_step_handler(sent, save_new_price)

def save_new_price(message):
    new_price = message.text
    if new_price.isdigit():
        try:
            supabase.table("settings").upsert({"key": "ticket_price", "value": new_price}).execute()
            bot.reply_to(message, f"✅ የዕጣ ዋጋ ወደ {new_price} ብር ተቀይሯል። ተጠቃሚዎች አሁን ይሄንን ዋጋ ያያሉ።")
        except Exception as e:
            bot.reply_to(message, f"❌ ዳታቤዝ ላይ ማስቀመጥ አልተቻለም፦ {str(e)}")
    else:
        bot.reply_to(message, "❌ ስህተት፦ እባክዎ ቁጥር ብቻ ይላኩ።")

# --- 6. USER TEXT HANDLING ---
@bot.message_handler(func=lambda m: True)
def handle_users(message):
    # እዚህ ጋር ለወደፊት የ SMS ማረጋገጫ ኮድ መጨመር ይቻላል
    bot.reply_to(message, "መልዕክትዎ ደርሶናል። ደረሰኝ ከሆነ እያረጋገጥን ነው፤ እባክዎ ትንሽ ይጠብቁ።")

if __name__ == "__main__":
    keep_alive()
    print("Bot is starting...")
    bot.infinity_polling()
