# --- 3. DATABASE ENGINE (FIXED) ---
def load_db():
    try:
        # በ DB_CHANNEL_ID ውስጥ ያሉትን የቅርብ መልእክቶች ለማግኘት 
        # ማሳሰቢያ፡ telebot በራሱ get_chat_history የለውም። 
        # እንደ አማራጭ ዳታውን ፋይል ላይ ማስቀመጥ ወይም የቅርብ ጊዜ መልእክትን በ ID መፈለግ ይቻላል።
        # ለጊዜው በ ID: 1 ጀምሮ ለመፈለግ እንዲህ ማድረግ ትችላለህ (ወይም ፒን የተደረገውን ተጠቀም)
        curr_chat = bot.get_chat(DB_CHANNEL_ID)
        if curr_chat.pinned_message and "💾 DB_STORAGE" in curr_chat.pinned_message.text:
            m_text = curr_chat.pinned_message.text
            loaded = json.loads(m_text.replace("💾 DB_STORAGE", "").strip())
            data.update(loaded)
            return True
    except Exception as e:
        print(f"Load DB Error: {e}")
    return False

# --- 5. HANDLERS (FIXED) ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_msgs(m):
    uid = str(m.from_user.id)
    # ተጠቃሚው ከዚህ በፊት በ /start ካልተመዘገበ እዚህ ጋር ይመዝገብ
    if uid not in data["users"]:
        data["users"][uid] = {"tks": 0, "wallet": 0, "name": m.from_user.first_name, "step": "", "sel_bid": None}
    
    u = data["users"][uid]
    
    # የ step ደህንነት (None check)
    current_step = u.get('step', "")

    if current_step.startswith("INPUT_AMT_") and int(uid) == ADMIN_ID:
        # ... የተቀረው ኮድህ
