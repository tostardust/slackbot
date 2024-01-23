import os
from dotenv import load_dotenv
from enum import Enum

load_dotenv()

USER_ID_1 = os.getenv('ERNAR')
USER_ID_2 = os.getenv('MAQSAT')
CHANNEL_ID = os.getenv('CHANNEL_ID')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CERT_PASSWORD = os.getenv('CERT_PASSWORD')