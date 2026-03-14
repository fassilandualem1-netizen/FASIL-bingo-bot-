import telebot
import os
from supabase import create_client, Client

# Railway Variables ውስጥ የሞላሃቸውን ስሞች እዚህ ይጠቀማል
TOKEN = os.getenv('BOT_TOKEN')
SB_URL = os.getenv('SUPABASE_URL')
SB_KEY = os.getenv('SUPABASE_KEY')

bot = telebot.TeleBot(TOKEN)

try:
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    print(f"Database Error: {e}")

@bot.message_handler(commands=['start'])
def start(message):
    try:
        # ዳታቤዝ መገናኘቱን መሞከሪያ
        supabase.table("users").upsert({"user_id": str(message.from_user.id)}).execute()
        bot.reply_to(message, "✅ ሰላም ፋሲል! አሁን በ Railway ላይ ዳታቤዙ በሚገባ ተገናኝቷል። ስራ መጀመር ትችላለህ።")
    except Exception as e:
        bot.reply_to(message, f"⚠️ ዳታቤዝ አልተገናኘም። ስህተቱ፦ {str(e)[:100]}")

bot.infinity_polling()
