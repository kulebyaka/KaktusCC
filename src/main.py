import asyncio
import logging
import signal
import sys
from .config import Config
from .database import DatabaseManager
from .scraper import KaktusScraper
from .bot import TelegramBot

logger = logging.getLogger(__name__)

class KaktusNotificationApp:
    def __init__(self):
        self.config = Config
        self.db_manager = None
        self.scraper = None
        self.bot = None
        self.running = False
        
    async def initialize(self):
        """Initialize all components."""
        try:
            Config.validate()
            Config.setup_logging()
            
            self.db_manager = DatabaseManager(self.config.DATABASE_URL)
            self.db_manager.create_tables()
            
            self.scraper = KaktusScraper(
                self.config.SCRAPE_URL,
                self.db_manager,
                self.config.CHECK_INTERVAL
            )
            
            self.bot = TelegramBot(self.config.TELEGRAM_BOT_TOKEN, self.db_manager)
            await self.bot.start_bot()
            
            logger.info("Application initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown of all components."""
        logger.info("Shutting down application...")
        self.running = False
        
        if self.bot:
            await self.bot.stop_bot()
        
        logger.info("Application shutdown complete")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Main application loop."""
        await self.initialize()
        
        self.setup_signal_handlers()
        self.running = True
        
        logger.info("Starting main application loop...")
        
        # Start bot polling updater
        await self.bot.application.updater.start_polling(drop_pending_updates=True)
        
        scraper_task = asyncio.create_task(
            self.scraper.start_monitoring(self.bot.handle_new_post)
        )
        
        try:
            while self.running:
                await asyncio.sleep(1)
                
                if scraper_task.done():
                    exception = scraper_task.exception()
                    if exception:
                        logger.error(f"Scraper task failed: {exception}")
                        scraper_task = asyncio.create_task(
                            self.scraper.start_monitoring(self.bot.handle_new_post)
                        )
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        
        finally:
            scraper_task.cancel()
            
            try:
                await scraper_task
            except asyncio.CancelledError:
                pass
            
            # Stop the updater
            await self.bot.application.updater.stop()
            
            await self.shutdown()

async def main():
    """Entry point for the application."""
    app = KaktusNotificationApp()
    
    try:
        await app.run()
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())