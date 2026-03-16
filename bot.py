import telebot

TOKEN = 'የአንተ_ቦት_ቶከን_እዚህ_ይግባ'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ሰላም! ቦቱ እየሰራ ነው።")

print("ቦቱ እየሰራ ነው...")
bot.infinity_polling()
