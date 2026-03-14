import telebot
import time

# ይህ ቶከን በትክክል መሃል ላይ ':' ስላለው አሁን ይሰራል
TOKEN = '8721334129:AAGhN-nLB0bs-auvy5M_XPznDn9z4xyFHoI'

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ ሰላም ፋሲል! አሁን ቦቱ በትክክል ሰርቷል። እንኳን ደስ አለህ!")

print("Bot is starting...")
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
