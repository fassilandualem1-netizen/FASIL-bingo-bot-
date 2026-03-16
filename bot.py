import os
import telebot

# Token-ን ከ Environment Variable ላይ ያነባል (ለደህንነት)
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "ሰላም! ቦቱ በ Render ላይ እየሰራ ነው።")

bot.infinity_polling()
