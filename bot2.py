# ================== JAVXAR AI BOT ==================
# All-in-one | Secure | Production-ready skeleton
# Created by Javxar

import os, time, sqlite3, logging
from telegram import Update, ReplyKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, PreCheckoutQueryHandler
from openai import OpenAI

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TG_MERCHANT_TOKEN = os.getenv("TG_MERCHANT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ================== LOGGING ==================
logging.basicConfig(level=logging.INFO)

# ================== AI CLIENT ==================
client = OpenAI(api_key=OPENAI_API_KEY)

# ================== DATABASE ==================
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    is_pro INTEGER DEFAULT 0,
    requests_today INTEGER DEFAULT 0,
    last_day TEXT
)
""")
db.commit()

# ================== HELPERS ==================
def today():
    return time.strftime("%Y-%m-%d")

def get_user(uid):
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    u = cur.fetchone()
    if not u:
        cur.execute("INSERT INTO users(user_id, last_day) VALUES(?,?)", (uid, today()))
        db.commit()
        return get_user(uid)
    return u

def inc_request(uid):
    u = get_user(uid)
    if u[3] != today():
        cur.execute("UPDATE users SET requests_today=0, last_day=? WHERE user_id=?", (today(), uid))
    cur.execute("UPDATE users SET requests_today=requests_today+1 WHERE user_id=?", (uid,))
    db.commit()

# ================== ANTI-SPAM ==================
LAST = {}
def anti_spam(uid, sec=3):
    now = time.time()
    if uid in LAST and now - LAST[uid] < sec:
        return False
    LAST[uid] = now
    return True

# ================== AI FUNCTIONS ==================
def ai_chat(text):
    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":text}]
        )
        return r.choices[0].message.content
    except Exception as e:
        return f"❌ AI xato berdi: {e}"

def ai_image(prompt):
    try:
        img = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        return img.data[0].url
    except Exception as e:
        return f"❌ Rasm yaratishda xato: {e}"

# ================== CONTENT ==================
def english_pro():
    return (
        "📘 English A1–B1\n\n"
        "A1: Alphabet, basic words\n"
        "A2: Tenses, daily speech\n"
        "B1: Speaking & writing\n\n"
        "Task: Describe your day in English."
    )

def prava_pro():
    return (
        "🚗 Prava Test (Professional)\n\n"
        "Q: Qizil svetofor?\n"
        "A) To‘xta ✅\nB) Yur\nC) Sekinlash"
    )

# ================== MENU ==================
MENU = ReplyKeyboardMarkup(
    [
        ["🤖 Savol", "🎨 Rasm"],
        ["📘 English", "🚗 Prava"],
        ["⭐ PRO", "📊 Statistika"]
    ],
    resize_keyboard=True
)

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Javxar AI Bot\n✨ Created by Javxar",
        reply_markup=MENU
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.message.from_user.id)
    await update.message.reply_text(
        f"📊 Statistika\nPRO: {'Yes' if u[1] else 'No'}\nSo‘rovlar bugun: {u[2]}"
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text

    if not anti_spam(uid):
        await update.message.reply_text("⏳ Sekinroq yoz 🙂")
        return

    u = get_user(uid)
    if not u[1] and u[2] >= 10:
        await update.message.reply_text("❌ Limit tugadi. PRO oling ⭐")
        return

    if text == "🤖 Savol":
        context.user_data["mode"] = "chat"
        await update.message.reply_text("Savolingni yoz")
        return

    if text == "🎨 Rasm":
        context.user_data["mode"] = "image"
        await update.message.reply_text("Prompt yoz")
        return

    if text == "📘 English":
        await update.message.reply_text(english_pro())
        return

    if text == "🚗 Prava":
        await update.message.reply_text(prava_pro())
        return

    if text == "📊 Statistika":
        await stats(update, context)
        return

    if text == "⭐ PRO":
        prices = [LabeledPrice("PRO – 30 kun", 10000 * 100)]
        await context.bot.send_invoice(
            chat_id=uid,
            title="Javxar AI PRO",
            description="Cheksiz AI + Premium funksiyalar",
            payload="PRO_SUB",
            provider_token=TG_MERCHANT_TOKEN,
            currency="UZS",
            prices=prices
        )
        return

    # ===== AI MODES =====
    inc_request(uid)

    if context.user_data.get("mode") == "chat":
        ans = ai_chat(text)
        await update.message.reply_text(ans)
    elif context.user_data.get("mode") == "image":
        url = ai_image(text)
        await update.message.reply_photo(url)
    else:
        await update.message.reply_text("Menyudan tanla 👆")

async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    cur.execute("UPDATE users SET is_pro=1 WHERE user_id=?", (uid,))
    db.commit()
    await update.message.reply_text("⭐ PRO faollashdi! Rahmat 🙌")

# ================== RUN ==================
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))
app.add_handler(PreCheckoutQueryHandler(precheckout))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
app.run_polling()
