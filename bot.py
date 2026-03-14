import telebot
import os

# ቶከኑን ከ Railway Variables ያነበዋል
TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ ተሳክቷል! ቦቱ አሁን በ Railway Variables ሰርቷል።")

bot.infinity_polling()
