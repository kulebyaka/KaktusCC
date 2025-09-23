# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot that monitors T-Mobile Kaktus webpage (https://www.mujkaktus.cz/chces-pridat) for promotional events and sends automated notifications to subscribers. Uses web scraping, PostgreSQL database, and Telegram's native message scheduling.

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m asyncio       # Async tests only

# Run specific test files
pytest tests/test_bot.py
pytest tests/test_scraper.py

# Run with coverage
pytest --cov=src --cov-report=html

# Test in Docker environment
docker-compose exec bot python -m pytest
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run local PostgreSQL for development
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=telegram_bot \
  -e POSTGRES_USER=bot \
  -e POSTGRES_PASSWORD=password \
  postgres:15-alpine

# Run bot locally (requires .env file)
python src/main.py

# Debug scraper independently
python debug-scraper.py

# Start test web server for local testing
python test_server.py
# Visit http://localhost:8080/admin to modify test events
```

### Docker Operations
```bash
# Local development with Docker
docker-compose up -d
docker-compose logs -f bot        # View bot logs
docker-compose logs -f db         # View database logs

# Production deployment (uses GHCR image)
docker-compose -f docker-compose.prod.yml up -d

# Build and test locally
docker-compose build
docker-compose up --build
```

## Architecture Overview

### Core Components

1. **KaktusNotificationApp** (`src/main.py`) - Main application orchestrator
   - Initializes all components with proper dependency order
   - Handles graceful shutdown via signal handlers
   - Manages async task lifecycle and restart logic
   - Coordinates between scraper and bot components

2. **KaktusScraper** (`src/scraper.py`) - Web monitoring engine
   - Fetches HTML from target URL every 5 minutes
   - Extracts event data using BeautifulSoup4
   - Calculates SHA256 hash for duplicate detection
   - Parses Czech datetime format: `DD.MM.YYYY HH:MM - HH:MM`

3. **TelegramBot** (`src/bot.py`) - User interaction handler
   - Handles `/start` and `/stop` commands
   - Sends immediate notifications to all active users
   - Schedules reminder messages using Telegram's native scheduling
   - Manages user blocking and rate limiting

4. **DatabaseManager** (`src/database.py`) - Data persistence layer
   - SQLAlchemy ORM with PostgreSQL backend
   - Two main tables: `users` and `processed_posts`
   - Handles user subscription state and post deduplication
   - Connection pooling and transaction management

### Key Design Patterns

- **Async/Await**: Main loop, bot polling, and scraping operations
- **Dependency Injection**: Components receive dependencies in constructor
- **Task Restart Logic**: Failed scraper tasks are automatically restarted
- **Graceful Shutdown**: Signal handlers ensure clean component teardown
- **Error Isolation**: Component failures don't crash the entire application

### Data Flow

1. Scraper fetches webpage every 5 minutes
2. HTML parsed and event data extracted
3. SHA256 hash checked against `processed_posts` table
4. If new post: immediate notification sent to all active users
5. Event datetime parsed and scheduled reminder queued via Telegram API
6. Post marked as processed to prevent re-sending

## Critical Configuration

### Environment Variables
- `TELEGRAM_BOT_TOKEN` - Required bot token from @BotFather
- `DATABASE_URL` - PostgreSQL connection string
- `SCRAPE_URL` - Target webpage (default: https://www.mujkaktus.cz/chces-pridat)
- `CHECK_INTERVAL` - Scraping interval in seconds (default: 300)
- `TZ` - Timezone for date parsing (default: Europe/Prague)

### Database Schema
```sql
-- Users table: subscription management
CREATE TABLE users (
    chat_id BIGINT PRIMARY KEY,           -- Telegram chat ID
    username VARCHAR(255),                -- Telegram username
    first_started TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,       -- Subscription status
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processed posts: deduplication tracking
CREATE TABLE processed_posts (
    id SERIAL PRIMARY KEY,
    post_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA256 of content
    title TEXT NOT NULL,                   -- Event title
    content TEXT NOT NULL,                 -- Full event description
    event_datetime TIMESTAMP WITH TIME ZONE, -- Parsed event start time
    notifications_sent BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Date/Time Parsing Rules

**Critical for functionality**: Bot must correctly parse Czech date format from titles.

- **Pattern**: `DD.MM.YYYY HH:MM - HH:MM`
- **Example**: `"Dobíječka 9.9.2025 15:00 - 18:00"`
- **Extract**: Start time only (first time occurrence)
- **Timezone**: Always interpret as Europe/Prague
- **Output**: Convert to UTC timestamp for Telegram API

**Implementation**: See `src/utils.py:parse_czech_datetime()`

## Telegram API Specifics

### Message Scheduling Implementation
- **Method**: Uses `python-telegram-bot` JobQueue with `run_once()` method
- **Limitation**: Telegram Bot API doesn't support native message scheduling
- **Implementation**: `schedule_reminder()` creates JobQueue job with delay until event time
- **Persistence**: Jobs are lost on bot restart (not database-backed)
- **Maximum delay**: Limited by JobQueue implementation (based on APScheduler)
- **Rate Limit**: 30 messages per second to different users

### Error Handling Requirements
1. **User Blocks Bot**: Mark user as inactive, don't retry
2. **Rate Limits**: Implement exponential backoff, batch messages
3. **Network Failures**: Retry with exponential backoff (scraper)
4. **Invalid Dates**: Skip scheduled message, log error
5. **Duplicate Posts**: Use hash comparison, never re-send

## Testing Architecture

### Test Categories
- **Unit tests** (`tests/test_*.py`): Individual component testing with mocks
- **Integration tests** (`tests/test_main.py`): Component interaction testing
- **Async tests**: All marked with `@pytest.mark.asyncio`

### Key Test Fixtures (`tests/conftest.py`)
- `test_db`: In-memory SQLite database for testing
- `db_manager`: Configured DatabaseManager instance
- `mock_telegram_bot`: Mocked Telegram bot for testing
- `sample_html`: Sample HTML content for scraper testing

### Test Execution Strategy
- Uses in-memory SQLite for fast database tests
- Mocks all external dependencies (HTTP requests, Telegram API)
- Comprehensive error scenario coverage
- Cross-platform compatibility (Windows/Linux/macOS)

## Debugging and Monitoring

### Debug Tools
- `debug-scraper.py`: Test scraper independently without database
- `test_server.py`: Local web server mimicking Kaktus website structure
- Docker logs: `docker-compose logs -f bot`

### Log Analysis
- All components use structured logging with timestamps
- Log levels: DEBUG (development), INFO (production)
- Key log points: New posts detected, notifications sent, errors

### Common Issues
1. **Wrong notification times**: Check timezone conversion in logs
2. **Duplicate notifications**: Verify `post_hash` calculation consistency
3. **Bot not responding**: Check bot token and user blocking status
4. **Scraper failures**: Review network connectivity and HTML structure changes
5. **Missing scheduled messages**: Check for bot restart (JobQueue jobs don't persist) or invalid event times

## Deployment Patterns

### Development
- Local Python with external PostgreSQL
- Full Docker Compose stack for integration testing
- Test server for controlled webpage simulation

### Production
- Uses pre-built GHCR image: `ghcr.io/kulebyaka/kaktuscc:latest`
- Production compose file: `docker-compose.prod.yml`
- Health checks and restart policies for reliability
- Volume persistence for database and logs