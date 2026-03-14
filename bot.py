import telebot
from supabase import create_client, Client

# መረጃዎቹን አሁኑኑ እዚህ እናረጋግጥ
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)

@bot.message_handler(commands=['start'])
def test_connection(message):
    try:
        # ዳታቤዙን "ሰላም" እንበለው
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        price = res.data[0]['value'] if res.data else "Unknown"
        
        bot.reply_to(message, f"✅ ግንኙነቱ ተሳክቷል!\n🎟 ዳታቤዝ ላይ ያለው ዋጋ፦ {price} ብር")
    except Exception as e:
        bot.reply_to(message, f"❌ ግንኙነቱ አልተሳካም! ስህተቱ፦ {str(e)[:50]}")

if __name__ == "__main__":
    bot.infinity_polling()
