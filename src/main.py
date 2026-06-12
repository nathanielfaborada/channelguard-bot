import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from telegram import Update

from src.bot.bot import build_bot_app
from src.database.database import add_subscriber, init_db
from src.envCore.env import (
    ADMIN_ID,
    CHANNEL_ID,
    CHANNEL_INVITE_LINK,
    WEBHOOK_URL,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot_app = build_bot_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await bot_app.initialize()
    await bot_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook/telegram")
    logger.info("Bot started!")
    yield
    await bot_app.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}


@app.post("/webhook/paymongo")
async def paymongo_webhook(request: Request):
    data = await request.json()

    try:
        event_type = data["data"]["attributes"]["type"]
        if event_type != "link.payment.paid":
            return {"ok": True}

        payment_data = data["data"]["attributes"]["data"]
        remarks = payment_data["attributes"]["remarks"]
        user_id, plan = remarks.split("|")
        user_id = int(user_id)

        plan_days = {
            "weekly": 7,
            "monthly": 30,
            "quarterly": 90,
            "lifetime": 36500,
        }
        days = plan_days.get(plan, 30)

        add_subscriber(user_id, "", "", plan, days)

        try:
            invite_link = await bot_app.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
                expire_date=datetime.now() + timedelta(days=1),
            )
            channel_link = invite_link.invite_link
        except Exception as exc:
            logger.error("Channel error: %s", exc)
            channel_link = CHANNEL_INVITE_LINK

        await bot_app.bot.send_message(
            user_id,
            f"Payment confirmed!\n\n"
            f"Welcome to ChannelGuard PH!\n\n"
            f"Click here to join the private channel:\n{channel_link}\n\n"
            f"This invite link expires in 24 hours.\n"
            f"Your subscription: {plan.capitalize()} ({days} days)",
        )

        await bot_app.bot.send_message(
            ADMIN_ID,
            f"New subscriber!\n\n"
            f"User ID: {user_id}\n"
            f"Plan: {plan.capitalize()}\n"
            f"Days: {days}",
        )
    except Exception as exc:
        logger.error("Webhook error: %s", exc)

    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "ChannelGuard Bot is running!"}
