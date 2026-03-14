import telebot
from supabase import create_client, Client
import time

# --- አዲሱ TOKEN እዚህ ገብቷል ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)

@bot.message_handler(commands=['start'])
def start(message):
    try:
        # ተጠቃሚውን መመዝገብ
        supabase.table("users").upsert({"user_id": str(message.from_user.id), "username": message.from_user.username}).execute()
        bot.reply_to(message, "✅ እንኳን ደስ አለህ ፋሲል! ቦቱ በአዲስ Token በሥርዓት መስራት ጀምሯል።\n\nአሁን የቢንጎ ጨዋታውን ለመጀመር ዝግጁ ነን።")
    except Exception as e:
        bot.reply_to(message, "ሰላም! ቦቱ ዝግጁ ነው።")

print("Bot is starting with the new token...")
while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
