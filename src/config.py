import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')
    SCRAPE_URL = os.getenv('SCRAPE_URL', 'https://www.mujkaktus.cz/chces-pridat')
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    TZ = os.getenv('TZ', 'Europe/Prague')
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
    
    @classmethod
    def setup_logging(cls):
        log_level = getattr(logging, cls.LOG_LEVEL.upper())
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/bot.log'),
                logging.StreamHandler()
            ]
        )
        
        # Reduce the verbosity of third-party libraries
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('telegram.ext.updater').setLevel(logging.WARNING)
        logging.getLogger('telegram.ext.Application').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)