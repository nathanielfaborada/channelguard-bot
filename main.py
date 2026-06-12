import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import requests
import sqlite3

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI()

# Telegram bot application
bot_app = (
    Application.builder()
    .token(BOT_TOKEN)
    .updater(None)
    .build()
)

# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        plan TEXT,
        expires_at TEXT,
        is_active INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        payment_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount INTEGER,
        plan TEXT,
        status TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

# ============ HELPERS ============
def get_subscriber(user_id):
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute("SELECT * FROM subscribers WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def add_subscriber(user_id, username, full_name, plan, days):
    expires_at = (datetime.now() + timedelta(days=days)).isoformat()
    conn = sqlite3.connect("subscribers.db")
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO subscribers 
                (user_id, username, full_name, plan, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, 1)''',
              (user_id, username, full_name, plan, expires_at))
    conn.commit()
    conn.close()

# ============ PAYMONGO ============
def create_payment_link(amount, description, user_id, plan):
    url = "https://api.paymongo.com/v1/links"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Basic {PAYMONGO_SECRET_KEY}"
    }
    payload = {
        "data": {
            "attributes": {
                "amount": amount * 100,  # Convert to centavos
                "description": description,
                "remarks": f"{user_id}|{plan}"
            }
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data["data"]["attributes"]["checkout_url"], data["data"]["id"]

# ============ BOT COMMANDS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📋 View Plans", callback_data="view_plans")],
        [InlineKeyboardButton("📊 My Status", callback_data="my_status")],
        [InlineKeyboardButton("💬 Support", url="https://t.me/yoursupport")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome, {user.first_name}!\n\n"
        f"🔐 *ChannelGuard PH*\n\n"
        f"Get exclusive access to our private channel by subscribing below!\n\n"
        f"Choose an option to get started:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "view_plans":
        keyboard = [
            [InlineKeyboardButton("📅 Weekly — ₱99", callback_data="plan_weekly_99_7")],
            [InlineKeyboardButton("📆 Monthly — ₱299", callback_data="plan_monthly_299_30")],
            [InlineKeyboardButton("🗓️ Quarterly — ₱799", callback_data="plan_quarterly_799_90")],
            [InlineKeyboardButton("♾️ Lifetime — ₱1999", callback_data="plan_lifetime_1999_36500")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "💎 *Choose Your Plan:*\n\n"
            "📅 Weekly — ₱99 (7 days)\n"
            "📆 Monthly — ₱299 (30 days)\n"
            "🗓️ Quarterly — ₱799 (90 days)\n"
            "♾️ Lifetime — ₱1,999 (Forever)\n\n"
            "Select a plan to proceed with payment:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif query.data.startswith("plan_"):
        parts = query.data.split("_")
        plan_name = parts[1]
        amount = int(parts[2])
        days = int(parts[3])

        try:
            checkout_url, payment_id = create_payment_link(
                amount,
                f"ChannelGuard PH - {plan_name.capitalize()} Plan",
                user.id,
                plan_name
            )

            # Save pending payment
            conn = sqlite3.connect("subscribers.db")
            c = conn.cursor()
            c.execute('''INSERT OR REPLACE INTO payments 
                        (payment_id, user_id, amount, plan, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                      (payment_id, user.id, amount, plan_name, "pending", datetime.now().isoformat()))
            conn.commit()
            conn.close()

            keyboard = [
                [InlineKeyboardButton("💳 Pay Now", url=checkout_url)],
                [InlineKeyboardButton("🔙 Back to Plans", callback_data="view_plans")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"💳 *Payment for {plan_name.capitalize()} Plan*\n\n"
                f"Amount: ₱{amount}\n"
                f"Duration: {days} days\n\n"
                f"Click the button below to proceed with payment via GCash, Maya, or Credit Card:\n\n"
                f"⚠️ After payment, access will be granted automatically!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Payment error: {e}")
            await query.edit_message_text("❌ Error creating payment. Please try again or contact support.")

    elif query.data == "my_status":
        subscriber = get_subscriber(user.id)
        if subscriber and subscriber[5] == 1:
            expires = datetime.fromisoformat(subscriber[4])
            days_left = (expires - datetime.now()).days
            await query.edit_message_text(
                f"✅ *Active Subscription*\n\n"
                f"Plan: {subscriber[3].capitalize()}\n"
                f"Expires: {expires.strftime('%B %d, %Y')}\n"
                f"Days Left: {days_left} days",
                parse_mode="Markdown"
            )
        else:
            keyboard = [[InlineKeyboardButton("📋 View Plans", callback_data="view_plans")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ *No Active Subscription*\n\n"
                "You don't have an active subscription yet.\n"
                "Click below to view our plans!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

    elif query.data == "back_start":
        keyboard = [
            [InlineKeyboardButton("📋 View Plans", callback_data="view_plans")],
            [InlineKeyboardButton("📊 My Status", callback_data="my_status")],
            [InlineKeyboardButton("💬 Support", url="https://t.me/yoursupport")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"👋 Welcome back!\n\n"
            f"🔐 *ChannelGuard PH*\n\n"
            f"Choose an option:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

# ============ WEBHOOK ROUTES ============
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}

@app.post("/webhook/paymongo")
async def paymongo_webhook(request: Request):
    data = await request.json()
    event_type = data["data"]["attributes"]["type"]

    if event_type == "link.payment.paid":
        payment_data = data["data"]["attributes"]["data"]
        remarks = payment_data["attributes"]["remarks"]
        user_id, plan = remarks.split("|")
        user_id = int(user_id)

        plan_days = {
            "weekly": 7,
            "monthly": 30,
            "quarterly": 90,
            "lifetime": 36500
        }
        days = plan_days.get(plan, 30)

        # Add to database
        add_subscriber(user_id, "", "", plan, days)

        # Add to channel
        try:
            await bot_app.bot.approve_chat_join_request(CHANNEL_ID, user_id)
        except:
            await bot_app.bot.unban_chat_member(CHANNEL_ID, user_id)

        # Notify user
        await bot_app.bot.send_message(
            user_id,
            f"✅ *Payment Confirmed!*\n\n"
            f"Welcome to ChannelGuard PH! 🎉\n\n"
            f"You now have access to the private channel!\n"
            f"Click here to join: {os.getenv('CHANNEL_INVITE_LINK', 'Check your channel list')}",
            parse_mode="Markdown"
        )

    return {"ok": True}

@app.on_event("startup")
async def startup():
    init_db()
    await bot_app.initialize()
    await bot_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook/telegram")
    logger.info("Bot started!")

@app.on_event("shutdown")
async def shutdown():
    await bot_app.shutdown()