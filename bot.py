import telebot
import re
import os
import time
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- CONFIG ---
TOKEN = '8721334129:AAEQQi1RtA6PKqTUg59sThJs6sRm_BnBr68'
SUPABASE_URL = 'https://htdqqcrgzmyegpovnppi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6Imh0ZHFxY3Jnem15ZWdwb3ZucHBpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM0MjQyMTIsImV4cCI6MjA4OTAwMDIxMn0.JH76fJ_11H3zVQRxLAhqm1SphfZkb5IWqqfi3jnZTC0'

ADMIN_ID = 8488592165            
GROUP_ID = -1003881429974        

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- SAFE DB CONNECTION ---
try:
    db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase Connected!")
except Exception as e:
    db = None
    print(f"❌ Supabase Connection Failed: {e}")

# --- DB HELPERS WITH ERROR HANDLING ---
def get_s():
    try:
        if db:
            res = db.table("game_state").select("value").eq("key", "current_game").execute()
            if res.data: return res.data[0]['value']
    except Exception as e: print(f"DB Read Error: {e}")
    return {"price": 20, "board": {}, "prizes": [0,0,0], "msg_id": None}

def get_u(uid):
    uid = str(uid)
    try:
        if db:
            res = db.table("users").select("*").eq("id", uid).execute()
            if res.data: return res.data[0]
            u = {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": ""}
            db.table("users").insert(u).execute()
            return u
    except Exception as e: print(f"User DB Error: {e}")
    return {"id": uid, "wallet": 0, "tickets": 0, "display_name": "Player", "step": ""}

# --- SIMPLE START FOR TESTING ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    print(f"Received /start from {message.from_user.id}")
    try:
        bot.reply_to(message, "✅ ቦቱ እየሰራ ነው! እንኳን ደህና መጡ።\nአሁን ዳታቤዙን እየፈተሽኩ ነው...")
        s = get_s()
        bot.send_message(message.chat.id, f"የአሁኑ መደብ: {s['price']} ብር ነው ተጫወቱ።")
    except Exception as e:
        print(f"Start Error: {e}")

# --- SMS AND OTHER HANDLERS ---
@bot.message_handler(func=lambda m: True)
def handle_all(m):
    # ደረሰኝ መኖሩን ቼክ ያደርጋል
    if re.search(r"(FT|DCA|[0-9]{10})", m.text):
        bot.reply_to(m, "📩 ደረሰኝህን አግኝቻለሁ! አድሚን እስኪያጸድቅ ድረስ ትንሽ ታገስ።")
        bot.send_message(ADMIN_ID, f"አዲስ ደረሰኝ ከ {m.from_user.id}:\n{m.text}")

# --- SERVER ---
@app.route('/')
def h(): return "Bot is Online"

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    print("🚀 Bot starting...")
    run_bot()
