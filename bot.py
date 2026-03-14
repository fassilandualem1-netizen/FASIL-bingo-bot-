import telebot
from supabase import create_client, Client

TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

bot = telebot.TeleBot(TOKEN)

# በደህንነት ለማገናኘት
supabase: Client = create_client(SB_URL, SB_KEY)

@bot.message_handler(commands=['start'])
def test_connection(message):
    try:
        # ዳታቤዙን በሌላ መንገድ እንጠይቀው (ቀጥታ Query)
        res = supabase.from_("settings").select("value").eq("key", "ticket_price").execute()
        
        if res.data:
            price = res.data[0]['value']
            bot.reply_to(message, f"✅ ተሳክቷል ፋሲል!\n🎟 ዋጋው፦ {price} ብር")
        else:
            bot.reply_to(message, "✅ ተሳክቷል! ግን 'settings' ሰንጠረዥ ውስጥ መረጃ የለም።")
            
    except Exception as e:
        bot.reply_to(message, f"❌ ስህተት፦ {str(e)}")

if __name__ == "__main__":
    bot.infinity_polling()
