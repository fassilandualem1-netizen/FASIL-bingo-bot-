import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os

# --- ኮንፊገሬሽን ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
CHANNEL_ID = -1003747262103  # ያንተ የቻናል ID
ADMIN_ID = 8488592165       # ያንተ ID
bot = telebot.TeleBot(TOKEN)

# --- WEB SERVER (ለ Render) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Active!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- ቼክ ማድረጊያ (Test Connection) ---
def check_channel():
    try:
        bot.send_message(CHANNEL_ID, "🔄 የቢንጎ ቦት ዳታቤዝ ግንኙነት ተመስርቷል!")
        return True
    except:
        return False

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        "🎰 **እንኳን ወደ ፋሲል ቢንጎ መጡ!**\n\n"
        "🎟 የዕጣ ዋጋ፦ **20 ብር**\n"
        "🏦 **CBE:** `1000XXXXXXXX` \n"
        "📲 **Telebirr:** `09XXXXXXXX` \n\n"
        "⚠️ ለመመዝገብ መጀመሪያ የባንክ ደረሰኝ (SMS) እዚህ ይላኩ።"
    )
    
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 የዛሬ ሪፖርት", "⚙️ ሰሌዳውን አጽዳ")
        bot.send_message(ADMIN_ID, f"🌟 **ሰላም ፋሲል (Admin)**\n\n{welcome_text}", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

# --- ደረሰኝ መቀበያ ---
@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    user_txt = message.text
    # ደረሰኝ መሆኑን ለመለየት (ለምሳሌ SMS ላይ ያሉ ቃላት)
    if any(word in user_txt.upper() for word in ["RECEIVED", "ETB", "ብር", "TRANSACTION"]):
        # 1. ለተጠቃሚው መልስ መስጠት
        bot.reply_to(message, "✅ ደረሰኙ ደርሶናል። አሁን ስምዎን ይላኩ።")
        
        # 2. ወደ ቻናሉ መረጃውን መላክ (እንደ ዳታቤዝ መጠቀም)
        log_text = (
            f"📩 **አዲስ የክፍያ ሙከራ**\n"
            f"👤 ተጠቃሚ፦ {message.from_user.first_name}\n"
            f"🆔 ID: `{message.from_user.id}`\n"
            f"📄 መረጃ፦ {user_txt[:150]}"
        )
        bot.send_message(CHANNEL_ID, log_text, parse_mode="Markdown")
    else:
        if message.from_user.id != ADMIN_ID:
            bot.reply_to(message, "እባክዎ የባንክ ደረሰኝ SMS እዚህ ይላኩ።")

if __name__ == "__main__":
    if check_channel():
        print("✅ Connection to Channel is Successful!")
    else:
        print("❌ Could not connect to Channel. Check Admin rights.")
        
    Thread(target=run_flask).start()
    bot.infinity_polling()
