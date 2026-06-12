import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PAYMONGO_SECRET_KEY = os.getenv("PAYMONGO_SECRET_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK")