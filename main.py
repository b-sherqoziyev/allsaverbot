from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

from config import BOT_TOKEN
from bot.handlers import router


async def main():
    """
    Main asynchronous function to configure and start the Telegram bot.

    This function:
    1. Initializes the bot with default properties and HTML parse mode
    2. Sets up the dispatcher with memory storage for finite state machine
    3. Includes all registered routers (handlers)
    4. Cleans up any pending updates via webhook
    5. Starts polling for updates from Telegram servers
    """

    # Initialize the bot instance with token from config
    # Default properties set HTML parse mode for messages
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Create dispatcher instance with in-memory storage for FSM
    # MemoryStorage is suitable for development and simple bots
    dp = Dispatcher(storage=MemoryStorage())

    # Include all handlers from the router
    # Router contains all the registered message and callback handlers
    dp.include_router(router)

    # Clean up any pending updates from previous sessions
    # This ensures the bot starts fresh without processing old updates
    await bot.delete_webhook(drop_pending_updates=True)

    # Start long-polling mode to receive updates from Telegram
    # This keeps the bot running and processing incoming messages
    await dp.start_polling(bot)


if __name__ == "__main__":
    """
    Entry point of the application.

    When executed directly (not imported as module):
    1. Creates and runs the asyncio event loop
    2. Executes the main() coroutine
    3. Handles proper event loop cleanup
    """

    # Run the main coroutine using asyncio.run()
    # This manages the event loop creation and cleanup
    asyncio.run(main())