import telebot
from telebot import types
from supabase import create_client, Client
import os

# --- CONFIG ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SB_URL = "https://htdqqcrgzmyegpovnppi.supabase.co"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZMi6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQyNDIxMiwiZXhwIjoyMDg5MDAwMjEyfQ.qa52FddJte01BIbVJ4P20R7NpfIzPWJtmHc_T2ozeTY"

bot = telebot.TeleBot(TOKEN)
supabase: Client = create_client(SB_URL, SB_KEY)
ADMIN_ID = 8488592165

# --- HELPERS ---
def get_price():
    try:
        res = supabase.table("settings").select("value").eq("key", "ticket_price").execute()
        return res.data[0]['value'] if res.data else "20"
    except: return "20"

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    u_id = message.from_user.id
    price = get_price()

    if u_id == ADMIN_ID:
        # ለአንተ የሚመጣው የአድሚን ፓነል
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔄 Reset Board", "💰 Set Price")
        bot.send_message(u_id, "እንኳን ደህና መጣህ ፋሲል! የአድሚን ፓነል ዝግጁ ነው።", reply_markup=markup)
    else:
        # ለተጠቃሚዎች የሚመጣው የምዝገባ መረጃ
        welcome_text = (
            f"🎰 **እንኳን ወደ ፋሲል ቢንጎ በሰላም መጡ!**\n\n"
            f"🎟 የዕጣ ዋጋ፦ **{price} ብር**\n"
            f"🏦 **CBE:** `1000XXXXXXXX` \n"
            f"📲 **Gasha/Telebirr:** `09XXXXXXXX` \n\n"
            "⚠️ ለመሳተፍ የባንክ ደረሰኝ (SMS) እዚህ ይላኩ።"
        )
        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_admin_tools(message):
    if message.from_user.id == ADMIN_ID:
        if message.text == "🔄 Reset Board":
            try:
                supabase.table("bingo_slots").update({"is_booked": False, "player_name": None}).neq("slot_number", 0).execute()
                bot.reply_to(message, "✅ የቢንጎ ሰሌዳው በሙሉ ጸድቷል!")
            except Exception as e:
                bot.reply_to(message, f"❌ ስህተት፦ {str(e)}")
        
        elif message.text == "💰 Set Price":
            sent = bot.reply_to(message, "አዲሱን የዕጣ ዋጋ በቁጥር ብቻ ይላኩ (ለምሳሌ፦ 15)፦")
            bot.register_next_step_handler(sent, update_price)
    else:
        # ለተራ ተጠቃሚ የሚሰጠው ምላሽ
        bot.reply_to(message, "መልዕክትዎ ደርሶኛል። ደረሰኝ ከሆነ እያረጋገጥን ነው...")

def update_price(message):
    new_price = message.text
    if new_price.isdigit():
        try:
            supabase.table("settings").upsert({"key": "ticket_price", "value": new_price}).execute()
            bot.reply_to(message, f"✅ የዕጣ ዋጋ ወደ {new_price} ብር ተቀይሯል።")
        except Exception as e:
            bot.reply_to(message, f"❌ ስህተት፦ {str(e)}")
    else:
        bot.reply_to(message, "❌ እባክዎ ቁጥር ብቻ ይላኩ።")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
