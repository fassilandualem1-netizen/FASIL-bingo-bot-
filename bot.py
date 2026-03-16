import telebot # በትንሽ i
import os
from flask import Flask
from threading import Thread

# --- SETUP ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ሰላም! ቦቱ በትክክል እየሰራ ነው። ✅")

# ለ Render/Heroku ሰርቨር እንዲነሳ የሚረዳ
@app.route('/')
def home():
    return "Bot is Alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    # ሰርቨሩን በሌላ Thread እናስነሳው
    t = Thread(target=run)
    t.start()
    
    print("ቦቱ መቆጠር ጀምሯል...")
    bot.infinity_polling()
