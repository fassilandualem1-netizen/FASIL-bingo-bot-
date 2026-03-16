# bot.py
import telebot
import config
from database import data, load_db, save_db
from admin_panel import register_admin_handlers, filter_sms
from threading import Thread
from flask import Flask

bot = telebot.TeleBot(config.TOKEN, threaded=False)
app = Flask(__name__)
register_admin_handlers(bot)

@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: 
        data["users"][uid] = {"wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    
    msg = (f"🌟 **እንኳን ወደ ፋሲል ልዩ ዕጣ በሰላም መጡ!** 🌟\n\n"
           f"📜 **ሕግና ደንብ፦**\n1. ክፍያ አስቀድመው መፈጸም አለብዎት።\n2. ደረሰኝ ሲልኩ በትክክል መሆኑን ያረጋግጡ።\n\n"
           f"💳 **የክፍያ አማራጮች፦**\n🏦 CBE: `{config.CBE_ACCOUNT}`\n📱 Telebirr: `{config.TELEBIRR_NUMBER}`\n\n"
           f"👇 ክፍያውን ከፈጸሙ በኋላ የደረሰኙን ፎቶ ወይም SMS እዚህ ይላኩ።")
    
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎰 ሰሌዳ ምረጥ", "🕹 ቁጥር ምረጥ", "💰 ዋሌት")
    bot.send_message(uid, msg, reply_markup=kb, parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'text'])
def handle_payment(m):
    uid = str(m.from_user.id)
    if m.text in ["🎰 ሰሌዳ ምረጥ", "🕹 ቁጥር ምረጥ", "💰 ዋሌት"]:
        handle_menu(m)
        return

    # ደረሰኝ ሲላክ
    bot.send_message(uid, "📩 ደረሰኝዎ ደርሶናል! እያረጋገጥን ስለሆነ እባክዎን ከ1-5 ደቂቃ በትዕግስት ይታገሱን። 🙏")
    
    kb = telebot.types.InlineKeyboardMarkup()
    if m.text:
        amt, tid = filter_sms(m.text)
        kb.add(telebot.types.InlineKeyboardButton(f"✅ አጽድቅ ({amt} ETB)", callback_data=f"ok_{uid}_{amt}_0"))
        kb.add(telebot.types.InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"no_{uid}"))
        bot.send_message(config.ADMIN_ID, f"📩 **አዲስ SMS ደረሰኝ**\n👤 ከ፦ {m.from_user.first_name}\n💰 መጠን፦ {amt}\n🆔 ID፦ {tid}\n\n`{m.text}`", reply_markup=kb, parse_mode="Markdown")
    
    elif m.photo:
        kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ (ብር ጻፍ)", callback_data=f"manual_{uid}"), # እዚህ ጋር ብር እንዲያስገባ ይጠይቃል
               telebot.types.InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"no_{uid}"))
        bot.send_photo(config.ADMIN_ID, m.photo[-1].file_id, caption=f"📩 **የፎቶ ደረሰኝ**\n👤 ከ፦ {m.from_user.first_name}", reply_markup=kb)

def handle_menu(m):
    uid = str(m.from_user.id)
    u = data["users"][uid]
    
    if m.text == "🎰 ሰሌዳ ምረጥ":
        kb = telebot.types.InlineKeyboardMarkup()
        for k, v in data["boards"].items():
            kb.add(telebot.types.InlineKeyboardButton(f"{v['name']} ({v['price']} ETB)", callback_data=f"sel_{k}"))
        bot.send_message(uid, "ለመጫወት የሚፈልጉትን ሰሌዳ ይምረጡ፦", reply_markup=kb)

    elif m.text == "💰 ዋሌት":
        bot.send_message(uid, f"💰 **የእርስዎ ዋሌት፦** `{u['wallet']} ETB`", parse_mode="Markdown")

    elif m.text == "🕹 ቁጥር ምረጥ":
        bid = u.get("sel_bid")
        if not bid:
            bot.send_message(uid, "⚠️ መጀመሪያ '🎰 ሰሌዳ ምረጥ' የሚለውን ተጭነው ሰሌዳ ይምረጡ።")
            return
        # የቁጥር ምርጫ ሎጅክ እዚህ ይቀጥላል...

@app.route('/')
def home(): return "Bot Running"

if __name__ == "__main__":
    load_db(bot)
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
