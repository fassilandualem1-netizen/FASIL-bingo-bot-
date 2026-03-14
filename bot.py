import telebot
from telebot import types
from flask import Flask
from threading import Thread
import os

TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
CHANNEL_ID = -1003747262103 
ADMIN_ID = 8488592165
bot = telebot.TeleBot(TOKEN)

# ለጊዜው መረጃን በሜሞሪ ለመያዝ (ቦቱ ሬስታርት ሲያደርግ ከቻናሉ እንዲያነብ እናደርገዋለን)
user_data = {}

app = Flask('')
@app.route('/')
def home(): return "Bingo Bot is Running!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- የቁጥር መምረጫ ሰሌዳ (Keyboard) ---
def create_bingo_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = []
    for i in range(1, 101):
        buttons.append(types.InlineKeyboardButton(str(i), callback_data=f"num_{i}"))
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    welcome = (f"🎰 **እንኳን ወደ ፋሲል ቢንጎ መጡ!**\n\n"
               f"🎟 የዕጣ ዋጋ፦ **20 ብር**\n"
               "⚠️ ለመሳተፍ መጀመሪያ የባንክ ደረሰኝ (SMS) እዚህ ይላኩ።")
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text

    # 1. ደረሰኝ ሲላክ
    if any(word in text.upper() for word in ["RECEIVED", "ETB", "ብር", "CBE"]):
        user_data[user_id] = {'step': 'name', 'sms': text}
        bot.reply_to(message, "✅ ደረሰኙ ታይቷል! አሁን በሰሌዳው ላይ የሚወጣውን **ሙሉ ስምዎን** ይላኩ።")
    
    # 2. ስም ሲላክ
    elif user_id in user_data and user_data[user_id].get('step') == 'name':
        user_data[user_id]['name'] = text
        user_data[user_id]['step'] = 'number'
        bot.send_message(message.chat.id, f"ደስ የሚል ነው {text}! አሁን የሚፈልጉትን ቁጥር ይምረጡ፡", 
                         reply_markup=create_bingo_keyboard())

# --- ቁጥር ሲመረጥ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("num_"))
def pick_number(call):
    user_id = call.from_user.id
    num = call.data.split("_")[1]

    if user_id in user_data and user_data[user_id].get('step') == 'number':
        name = user_data[user_id]['name']
        sms = user_data[user_id]['sms']

        # ወደ ዳታቤዝ ቻናል መላክ (በሰንጠረዥ መልክ)
        db_entry = (
            f"📌 **አዲስ ምዝገባ**\n"
            f"👤 ስም፦ {name}\n"
            f"🔢 ቁጥር፦ {num}\n"
            f"🆔 UserID: `{user_id}`\n"
            f"📝 SMS፦ {sms[:50]}..."
        )
        bot.send_message(CHANNEL_ID, db_entry, parse_mode="Markdown")
        
        # ለተጫዋቹ ማረጋገጫ
        bot.edit_message_text(f"✅ ተሳክቷል! ቁጥር **{num}** ለስምዎ ({name}) ተመዝግቧል። መልካም ዕድል!", 
                              call.message.chat.id, call.message.message_id)
        del user_data[user_id] # ዳታውን ከሜሞሪ አጽዳ
    else:
        bot.answer_callback_query(call.id, "⚠️ እባክዎ መጀመሪያ ደረሰኝ ይላኩ።")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
