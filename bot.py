import telebot
from flask import Flask
from threading import Thread
import os

TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
bot = telebot.TeleBot(TOKEN)

app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ ሰላም ፋሲል! ቦቱ አሁን ዳታቤዝ ሳይጠቀም እየሰራ ነው። አሁን ችግሩ ዳታቤዝ ላይ እንደሆነ አረጋግጠናል!")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
