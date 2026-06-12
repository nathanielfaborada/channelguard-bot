import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.database.database import add_payment, get_subscriber
from src.paymongo.payment_link import create_payment_link

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("View Plans", callback_data="view_plans")],
        [InlineKeyboardButton("My Status", callback_data="my_status")],
        [InlineKeyboardButton("Support", url="https://t.me/yoursupport")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Welcome, {user.first_name}!\n\n"
        f"*ChannelGuard PH*\n\n"
        f"Get exclusive access to our private channel by subscribing below.\n\n"
        f"Choose an option to get started:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "view_plans":
        await show_plans(query)
    elif query.data.startswith("plan_"):
        await handle_plan_selection(query, user)
    elif query.data == "my_status":
        await show_status(query, user)
    elif query.data == "back_start":
        await show_start_menu(query)


async def show_plans(query):
    keyboard = [
        [InlineKeyboardButton("Weekly - PHP 99", callback_data="plan_weekly_99_7")],
        [InlineKeyboardButton("Monthly - PHP 299", callback_data="plan_monthly_299_30")],
        [InlineKeyboardButton("Quarterly - PHP 799", callback_data="plan_quarterly_799_90")],
        [InlineKeyboardButton("Lifetime - PHP 1999", callback_data="plan_lifetime_1999_36500")],
        [InlineKeyboardButton("Back", callback_data="back_start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "*Choose Your Plan:*\n\n"
        "Weekly - PHP 99 (7 days)\n"
        "Monthly - PHP 299 (30 days)\n"
        "Quarterly - PHP 799 (90 days)\n"
        "Lifetime - PHP 1,999 (Forever)\n\n"
        "Select a plan to proceed with payment:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def handle_plan_selection(query, user):
    parts = query.data.split("_")
    plan_name = parts[1]
    amount = int(parts[2])
    days = int(parts[3])

    try:
        checkout_url, payment_id = create_payment_link(
            amount,
            f"ChannelGuard PH - {plan_name.capitalize()} Plan",
            user.id,
            plan_name,
        )

        add_payment(
            payment_id,
            user.id,
            amount,
            plan_name,
            "pending",
            datetime.now().isoformat(),
        )

        keyboard = [
            [InlineKeyboardButton("Pay Now", url=checkout_url)],
            [InlineKeyboardButton("Back to Plans", callback_data="view_plans")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"*Payment for {plan_name.capitalize()} Plan*\n\n"
            f"Amount: PHP {amount}\n"
            f"Duration: {days} days\n\n"
            f"Click below to pay via GCash, Maya, or Credit Card.\n\n"
            f"Access will be granted automatically after payment.",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Payment error: %s", exc)
        await query.edit_message_text("Error creating payment. Please try again.")


async def show_status(query, user):
    subscriber = get_subscriber(user.id)

    if subscriber and subscriber[5] == 1:
        expires = datetime.fromisoformat(subscriber[4])
        days_left = (expires - datetime.now()).days

        await query.edit_message_text(
            f"*Active Subscription*\n\n"
            f"Plan: {subscriber[3].capitalize()}\n"
            f"Expires: {expires.strftime('%B %d, %Y')}\n"
            f"Days Left: {days_left} days",
            parse_mode="Markdown",
        )
        return

    keyboard = [[InlineKeyboardButton("View Plans", callback_data="view_plans")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "*No Active Subscription*\n\n"
        "You don't have an active subscription yet.\n"
        "Click below to view our plans.",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def show_start_menu(query):
    keyboard = [
        [InlineKeyboardButton("View Plans", callback_data="view_plans")],
        [InlineKeyboardButton("My Status", callback_data="my_status")],
        [InlineKeyboardButton("Support", url="https://t.me/yoursupport")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Welcome back!\n\n"
        "*ChannelGuard PH*\n\n"
        "Choose an option:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
