# --- የ Wallet እና የቁጥር ምርጫ Logic ማሻሻያ ---

@bot.callback_query_handler(func=lambda c: True)
def handle_calls(c):
    uid = str(c.from_user.id)
    u = data["users"].get(uid)

    # 1. አድሚኑ ደረሰኝ ሲያጸድቅ (ብሩን ዋሌት ላይ ብቻ መጨመር)
    if c.data.startswith("ok_") and int(uid) == ADMIN_ID:
        _, t_uid, amt, bid = c.data.split("_")
        amt_val = float(amt)
        
        # ብሩን በቀጥታ ዋሌት ላይ መደመር (እጣ ወዲያው አንሰጥም)
        data["users"][t_uid]["wallet"] = data["users"][t_uid].get("wallet", 0) + amt_val
        data["users"][t_uid]["step"] = "ASK_NAME" if not data["users"][t_uid].get("name") else ""
        
        msg = f"✅ ደረሰኝዎ ጸድቋል!\n💰 {amt_val} ETB ዋሌትዎ ላይ ተጨምሯል።\n"
        msg += "አሁን '🕹 ቁጥር ምረጥ' የሚለውን በመጫን መጫወት ይችላሉ።"
        
        bot.send_message(t_uid, msg)
        bot.delete_message(ADMIN_ID, c.message.message_id)
        save_db()

    # 2. ቁጥር ሲመረጥ (ከዋሌት ላይ ቀንሶ እጣ መስጠት)
    elif c.data.startswith("n_"):
        bid = u.get("sel_bid")
        if not bid:
            bot.answer_callback_query(c.id, "⚠️ እባክህ መጀመሪያ ሰሌዳ ምረጥ!", show_alert=True)
            return
            
        b = data["boards"][bid]
        price = b["price"]
        n = c.data.split("_")[1]

        # ዋሌቱን ቼክ ማድረግ
        if u.get("wallet", 0) >= price:
            if n not in b["slots"]:
                # ብር መቀነስ
                u["wallet"] -= price
                # ቁጥሩን መመዝገብ
                b["slots"][n] = {"name": u["name"], "id": uid}
                
                refresh_group(bid)
                bot.answer_callback_query(c.id, f"✅ ቁጥር {n} ተመርጧል! {price} ETB ከዋሌትዎ ተቀንሷል።")
                
                # የቁጥር መምረጫውን ዝጋው ወይም አድሰው
                bot.delete_message(uid, c.message.message_id)
                save_db()
            else:
                bot.answer_callback_query(c.id, "⚠️ ይቅርታ፣ ይህ ቁጥር ተይዟል!", show_alert=True)
        else:
            bot.answer_callback_query(c.id, f"❌ በቂ ብር የለዎትም! የሰሌዳው ዋጋ {price} ETB ነው።", show_alert=True)

# --- UI ማሻሻያ (Reply Keyboard ላይ የዋሌት በተን መጨመር) ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in data["users"]: 
        data["users"][uid] = {"wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None, "tks": 0}
    
    main_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # እዚህ ጋር "💰 ዋሌት" የሚል በተን ጨምረናል
    main_kb.add("🕹 ቁጥር ምረጥ", "💰 ዋሌትና መረጃ", "🎫 የእኔ እጣ")
    if int(uid) == ADMIN_ID: main_kb.add("🛠 Admin Panel")
    
    bot.send_message(uid, "🌟 **እንኳን ወደ ፋሲል ልዩ ዕጣ በሰላም መጡ!** 🌟", reply_markup=main_kb, parse_mode="Markdown")
