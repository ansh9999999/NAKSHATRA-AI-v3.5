import os
from dotenv import load_dotenv

load_dotenv()

# Delta Exchange
DELTA_API_KEY = os.getenv("DELTA_API_KEY")
DELTA_API_SECRET = os.getenv("DELTA_API_SECRET")
BASE_URL = "https://api.india.delta.exchange"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ntfy
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

# Scanner
SYMBOLS = [
    "BTCUSD",
    "ETHUSD"
]

TIMEFRAME = "5m"
CANDLE_LIMIT = 200
SCAN_INTERVAL = 300  # seconds
