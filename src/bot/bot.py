from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from src.bot.handlers import button_handler, start
from src.envCore.env import BOT_TOKEN


def build_bot_app():
    application = Application.builder().token(BOT_TOKEN).updater(None).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    return application
