# admin panel.py
import telebot
import config
from database import data, save_db

def register_admin_handlers(bot):
    # --- የአድሚን ዋና ሜኑ ---
    @bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel" and m.from_user.id == config.ADMIN_ID)
    def admin_main_menu(m):
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            telebot.types.InlineKeyboardButton("♻️ Reset & Board (ሰሌዳ አጽዳ)", callback_data="adm_reset_main"),
            telebot.types.InlineKeyboardButton("💵 ዋጋ ቀይር", callback_data="adm_price_main"),
            telebot.types.InlineKeyboardButton("🏆 ሽልማት ወስን", callback_data="adm_prize_main"),
            telebot.types.InlineKeyboardButton("🟢/🔴 ሰሌዳ ኦን ኦፍ", callback_data="adm_toggle_main")
        )
        bot.send_message(config.ADMIN_ID, "🛠 **የአድሚን መቆጣጠሪያ ክፍል**\nእባክዎ መለወጥ የሚፈልጉትን ተግባር ይምረጡ፦", reply_markup=kb, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
    def handle_admin_nav(c):
        action = c.data
        kb = telebot.types.InlineKeyboardMarkup(row_width=1)
        
        # 1. Reset ምርጫ
        if action == "adm_reset_main":
            for k in data["boards"]:
                kb.add(telebot.types.InlineKeyboardButton(f"ሰሌዳ {k} አጽዳ", callback_data=f"do_reset_{k}"))
            bot.edit_message_text("የቱን ሰሌዳ ማጽዳት ይፈልጋሉ?", config.ADMIN_ID, c.message.message_id, reply_markup=kb)

        # 2. ዋጋ ቀይር ምርጫ
        elif action == "adm_price_main":
            for k in data["boards"]:
                kb.add(telebot.types.InlineKeyboardButton(f"የሰሌዳ {k} ዋጋ ቀይር", callback_data=f"set_price_{k}"))
            bot.edit_message_text("ዋጋ ለመቀየር ሰሌዳ ይምረጡ፦", config.ADMIN_ID, c.message.message_id, reply_markup=kb)

        # 3. ሽልማት ወስን ምርጫ
        elif action == "adm_prize_main":
            for k in data["boards"]:
                kb.add(telebot.types.InlineKeyboardButton(f"የሰሌዳ {k} ሽልማት ወስን", callback_data=f"set_prize_{k}"))
            bot.edit_message_text("ሽልማት ለመወሰን ሰሌዳ ይምረጡ፦", config.ADMIN_ID, c.message.message_id, reply_markup=kb)

        # 4. On/Off ምርጫ
        elif action == "adm_toggle_main":
            for k, v in data["boards"].items():
                status = "🟢 ON" if v["active"] else "🔴 OFF"
                kb.add(telebot.types.InlineKeyboardButton(f"ሰሌዳ {k} ({status})", callback_data=f"do_toggle_{k}"))
            bot.edit_message_text("ሰሌዳ ለመክፈት ወይም ለመዝጋት ይጫኑ፦", config.ADMIN_ID, c.message.message_id, reply_markup=kb)

    # --- የተግባራት አፈጻጸም (Execution) ---
    @bot.callback_query_handler(func=lambda c: any(c.data.startswith(pre) for pre in ["do_reset_", "do_toggle_", "set_price_", "set_prize_"]))
    def execute_admin_tasks(c):
        cmd = c.data.split("_")
        task = cmd[1]
        bid = cmd[2]

        if task == "reset":
            data["boards"][bid]["slots"] = {}
            save_db(bot)
            bot.answer_callback_query(c.id, f"✅ ሰሌዳ {bid} በትክክል ጸድቷል!")
            bot.send_message(config.ADMIN_ID, f"♻️ ሰሌዳ {bid} ባዶ ሆኗል።")

        elif task == "toggle":
            data["boards"][bid]["active"] = not data["boards"][bid]["active"]
            status = "ክፍት" if data["boards"][bid]["active"] else "ዝግ"
            save_db(bot)
            bot.answer_callback_query(c.id, f"ሰሌዳ {bid} አሁን {status} ነው")
            # ወደ ኋላ ለመመለስ ሜኑውን መልሶ ያሳያል
            admin_main_menu(c.message) 

        elif task == "price":
            msg = bot.send_message(config.ADMIN_ID, f"✍️ ለሰሌዳ {bid} አዲስ ዋጋ (Price) በቁጥር ብቻ ይጻፉ፦")
            bot.register_next_step_handler(msg, update_price, bid)

        elif task == "prize":
            msg = bot.send_message(config.ADMIN_ID, f"✍️ ለሰሌዳ {bid} 3ቱንም ሽልማቶች በኮማ ለይተው ይጻፉ (ለምሳሌ፦ 500,300,100)፦")
            bot.register_next_step_handler(msg, update_prize, bid)

    # --- የዋጋ እና ሽልማት መቀበያ ሎጂክ ---
    def update_price(m, bid):
        try:
            new_price = int(m.text)
            data["boards"][bid]["price"] = new_price
            save_db(bot)
            bot.send_message(config.ADMIN_ID, f"✅ የሰሌዳ {bid} ዋጋ ወደ {new_price} ETB ተቀይሯል።")
        except:
            bot.send_message(config.ADMIN_ID, "❌ ስህተት! እባክዎ ቁጥር ብቻ ያስገቡ።")

    def update_prize(m, bid):
        try:
            p_list = [int(x.strip()) for x in m.text.split(',')]
            if len(p_list) == 3:
                data["boards"][bid]["prizes"] = p_list
                save_db(bot)
                bot.send_message(config.ADMIN_ID, f"✅ የሰሌዳ {bid} ሽልማቶች ተቀምጠዋል።")
            else:
                bot.send_message(config.ADMIN_ID, "❌ ስህተት! የግድ 3 ሽልማቶችን በኮማ መለየት አለብዎት።")
        except:
            bot.send_message(config.ADMIN_ID, "❌ ስህተት! በትክክል ያስገቡ (ምሳሌ፦ 500,300,100)።")
