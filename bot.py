import telebot
import os
from flask import Flask
from threading import Thread

# የአንተ ትክክለኛ ቶከን
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ሰላም! አሁን ቦቱ በትክክል እየሰራ ነው። ✅")

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    # Flask በሌላ Thread ይነሳል (ለ Render እና ለ GitHub Build)
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    print("ቦቱ እየሰራ ነው...")
    bot.infinity_polling()
