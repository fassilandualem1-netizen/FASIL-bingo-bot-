# bot.py
import telebot
import config
from database import data, load_db, save_db
from admin_panel import register_admin_handlers, filter_sms
from threading import Thread
from flask import Flask

# 1. ቦቱን ማስጀመር
bot = telebot.TeleBot(config.TOKEN, threaded=False)
app = Flask(__name__)

# 2. የአድሚን መቆጣጠሪያዎችን መመዝገብ
register_admin_handlers(bot)

# --- የግሩፕ ሰሌዳን የማደሻ ፋንክሽን ---
def refresh_group_board(bid):
    b = data["boards"][bid]
    status = "🟢 ክፍት" if b["active"] else "🔴 ዝግ"
    
    txt = f"🔥 **{b['name']}** {status}\n"
    txt += f"━━━━━━━━━━━━━\n"
    txt += f"💵 **መደብ:** `{b['price']} ETB` | 🎁 **ሽልማት:** `{sum(b['prizes'])} ETB` \n"
    txt += f"━━━━━━━━━━━━━\n"
    
    for i in range(1, b["max"] + 1):
        n = str(i)
        txt += f"{i:02d}.{b['slots'][n]['name'][:4]}🏆 " if n in b["slots"] else f"{i:02d}.⚪️ "
        if i % 3 == 0: txt += "\n"
        
    txt += f"\n💰 🥇{b['prizes'][0]} | 🥈{b['prizes'][1]} | 🥉{b['prizes'][2]}\n"
    txt += f"━━━━━━━━━━━━━\n"
    txt += f"🕹 @{bot.get_me().username}"

    try:
        if not b.get("msg_id"):
            m = bot.send_message(config.GROUP_ID, txt, parse_mode="Markdown")
            b["msg_id"] = m.message_id
            bot.pin_chat_message(config.GROUP_ID, m.message_id)
        else:
            bot.edit_message_text(txt, config.GROUP_ID, b["msg_id"], parse_mode="Markdown")
    except: pass
    save_db(bot)

# --- /start ሲባል የሚመጣ ሰላምታ ---
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
    kb.add("🎰 ሰሌዳ ምረጥ", "🕹 ቁጥር ምረጥ")
    kb.add("💰 ዋሌት", "🎫 የእኔ እጣ")
    if int(uid) == config.ADMIN_ID: kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, msg, reply_markup=kb, parse_mode="Markdown")

# --- መልእክቶችን መቀበያ እና ማስተናገጃ ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_msgs(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: return
    u = data["users"][uid]

    # 1. ስም መቀበያ ሁኔታ ላይ ከሆነ
    if u.get("step") == "ASK_NAME":
        u["name"] = m.text
        u["step"] = ""
        save_db(bot)
        bot.send_message(uid, f"✅ ስምዎ '{m.text}' ተብሎ ተመዝግቧል። አሁን '🕹 ቁጥር ምረጥ' የሚለውን ይጫኑ።")
        return

    # 2. የሜኑ በተኖች
    if m.text == "🎰 ሰሌዳ ምረጥ":
        kb = telebot.types.InlineKeyboardMarkup()
        for k, v in data["boards"].items():
            if v["active"]:
                kb.add(telebot.types.InlineKeyboardButton(f"{v['name']} ({v['price']} ETB)", callback_data=f"sel_{k}"))
        bot.send_message(uid, "ለመጫወት የሚፈልጉትን ሰሌዳ ይምረጡ፦", reply_markup=kb)

    elif m.text == "💰 ዋሌት":
        bot.send_message(uid, f"💰 **የእርስዎ ዋሌት፦** `{u['wallet']} ETB`", parse_mode="Markdown")

    elif m.text == "🕹 ቁጥር ምረጥ":
        bid = u.get("sel_bid")
        if not bid:
            bot.send_message(uid, "⚠️ መጀመሪያ '🎰 ሰሌዳ ምረጥ' የሚለውን ተጭነው ሰሌዳ ይምረጡ።")
            return
        
        b = data["boards"][bid]
        if u["wallet"] < b["price"]:
            bot.send_message(uid, f"❌ ቀሪ ሂሳብዎ ({u['wallet']} ETB) ከሰሌዳው መደብ ያነሰ ነው። እባክዎ መጀመሪያ ብር ይላኩ።")
            return

        kb = telebot.types.InlineKeyboardMarkup(row_width=5)
        btns = [telebot.types.InlineKeyboardButton(str(i), callback_data=f"n_{i}") 
                for i in range(1, b["max"]+1) if str(i) not in b["slots"]]
        kb.add(*btns)
        bot.send_message(uid, f"🔢 ከ{b['name']} ቁጥር ይምረጡ፦", reply_markup=kb)

    # 3. ደረሰኝ ሲላክ (ፎቶ ወይም ጽሁፍ)
    elif m.content_type == 'photo' or (m.text and not m.text.startswith("/")):
        bot.send_message(uid, "📩 ደረሰኝዎ ደርሶናል! እያረጋገጥን ስለሆነ እባክዎን ከ1-5 ደቂቃ በትዕግስት ይታገሱን። 🙏")
        
        kb = telebot.types.InlineKeyboardMarkup()
        if m.text:
            amt, tid = filter_sms(m.text)
            kb.add(telebot.types.InlineKeyboardButton(f"✅ አጽድቅ ({amt} ETB)", callback_data=f"ok_{uid}_{amt}"))
            kb.add(telebot.types.InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"no_{uid}"))
            bot.send_message(config.ADMIN_ID, f"📩 **አዲስ SMS ደረሰኝ**\n👤 ከ፦ {m.from_user.first_name}\n💰 መጠን፦ {amt}\n🆔 ID፦ {tid}\n\n`{m.text}`", reply_markup=kb)
        
        elif m.photo:
            kb.add(telebot.types.InlineKeyboardButton("✅ አጽድቅ (ብር ጻፍ)", callback_data=f"manual_{uid}"),
                   telebot.types.InlineKeyboardButton("❌ ውድቅ አድርግ", callback_data=f"no_{uid}"))
            bot.send_photo(config.ADMIN_ID, m.photo[-1].file_id, caption=f"📩 **የፎቶ ደረሰኝ**\n👤 ከ፦ {m.from_user.first_name}", reply_markup=kb)

# --- የ Inline Button ጥሪዎችን ማስተናገጃ ---
@bot.callback_query_handler(func=lambda c: c.data.startswith(("sel_", "n_")))
def user_callbacks(c):
    uid = str(c.from_user.id)
    u = data["users"].get(uid)
    if not u: return

    if c.data.startswith("sel_"):
        bid = c.data.split("_")[1]
        u["sel_bid"] = bid
        u["step"] = "ASK_NAME" if not u.get("name") else ""
        save_db(bot)
        txt = f"✅ ሰሌዳ {bid} ተመርጧል!"
        if u["step"] == "ASK_NAME": txt += "\n\nእባክዎ መጀመሪያ ስምዎን ያስገቡ፦"
        bot.edit_message_text(txt, uid, c.message.message_id)

    elif c.data.startswith("n_"):
        bid = u.get("sel_bid")
        num = c.data.split("_")[1]
        b = data["boards"][bid]

        if u["wallet"] >= b["price"]:
            if num not in b["slots"]:
                b["slots"][num] = {"name": u["name"], "id": uid}
                u["wallet"] -= b["price"]
                bot.answer_callback_query(c.id, f"✅ ቁጥር {num} ተመዝግቧል!")
                bot.delete_message(uid, c.message.message_id)
                bot.send_message(uid, f"🎉 ቁጥር {num} ተይዟል! ቀሪ ዋሌት፦ {u['wallet']} ETB")
                refresh_group_board(bid)
            else:
                bot.answer_callback_query(c.id, "⚠️ ይህ ቁጥር ተይዟል!", show_alert=True)
        else:
            bot.answer_callback_query(c.id, "❌ ቀሪ ሂሳብዎ አነስተኛ ነው!", show_alert=True)

# --- ሰርቨር ማስነሻ ---
@app.route('/')
def home(): return "Bot Active"

if __name__ == "__main__":
    load_db(bot)
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    print("ቦቱ ስራ ጀምሯል...")
    bot.infinity_polling()
