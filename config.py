"""
Configuration module for the Telegram bot.
Handles environment variables and sensitive settings like the bot token.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Get the bot token from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")