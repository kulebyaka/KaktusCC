import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from datetime import datetime
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, DatabaseManager
from src.config import Config

@pytest.fixture
def temp_env():
    """Fixture to set temporary environment variables for testing."""
    original_env = os.environ.copy()
    
    test_env = {
        'TELEGRAM_BOT_TOKEN': 'test_token_123',
        'DATABASE_URL': 'sqlite:///:memory:',
        'SCRAPE_URL': 'https://test.example.com',
        'CHECK_INTERVAL': '60',
        'LOG_LEVEL': 'DEBUG',
        'TZ': 'Europe/Prague'
    }
    
    os.environ.update(test_env)
    
    yield test_env
    
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def test_db():
    """Fixture to create a test database."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield engine, SessionLocal
    
    engine.dispose()

@pytest.fixture
def db_manager(test_db):
    """Fixture to create a DatabaseManager with test database."""
    engine, session_local = test_db
    
    db_manager = DatabaseManager('sqlite:///:memory:')
    db_manager.engine = engine
    db_manager.SessionLocal = session_local
    
    return db_manager

@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot for testing."""
    mock_bot = Mock()
    mock_bot.send_message.return_value = None
    return mock_bot

@pytest.fixture
def mock_requests_get():
    """Mock requests.get for testing web scraping."""
    with patch('requests.Session.get') as mock_get:
        yield mock_get

@pytest.fixture
def sample_post_data():
    """Sample post data for testing."""
    prague_tz = pytz.timezone('Europe/Prague')
    event_time = prague_tz.localize(datetime(2025, 9, 9, 15, 0))
    
    return {
        'title': 'Dobíječka 9.9.2025 15:00 - 18:00',
        'content': 'Test content for Kaktus event',
        'event_datetime': event_time,
        'post_hash': 'test_hash_123'
    }

@pytest.fixture
def sample_html():
    """Sample HTML content for scraper testing."""
    return '''
    <html>
        <body>
            <article>
                <h2>Dobíječka 9.9.2025 15:00 - 18:00</h2>
                <div class="content">
                    <p>Test content for Kaktus event</p>
                </div>
            </article>
        </body>
    </html>
    '''