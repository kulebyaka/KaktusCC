# Kaktus Telegram Notification Bot

A Telegram bot that monitors the T-Mobile Kaktus webpage for new promotional events and sends automated notifications to subscribed users. When a new event is posted, the bot sends an immediate notification and schedules a reminder for when the event starts.

## Features

- **Automated Monitoring**: Checks https://www.mujkaktus.cz/chces-pridat every 5 minutes for new posts
- **Instant Notifications**: Sends immediate alerts when new events are detected
- **Smart Scheduling**: Automatically schedules reminder messages for event start times using Telegram's native scheduling
- **Duplicate Prevention**: Uses SHA256 hashing to avoid sending duplicate notifications
- **Prague Timezone Support**: Properly handles Czech date/time formats (`DD.MM.YYYY HH:MM - HH:MM`)
- **User Management**: Simple subscription system with `/start` and `/stop` commands
- **Robust Error Handling**: Network retries, rate limiting, and graceful failure handling

## Quick Start with Docker

### Using Pre-built Image from GHCR

1. **Set environment variables:**
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export GITHUB_REPOSITORY="kulebyaka/kaktuscc"
```

2. **Run with Docker Compose:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Building Locally

1. **Copy environment file:**
```bash
cp .env.example .env
# Edit .env with your bot token
```

2. **Run with Docker Compose:**
```bash
docker-compose up -d
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather | **Required** |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://bot:password@db:5432/telegram_bot` |
| `SCRAPE_URL` | URL to monitor for events | `https://www.mujkaktus.cz/chces-pridat` |
| `CHECK_INTERVAL` | Check interval in seconds | `300` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `TZ` | Timezone | `Europe/Prague` |

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Subscribe to event notifications |
| `/stop` | Unsubscribe from notifications |

## How It Works

### Event Processing Flow

1. **Web Scraping**: Monitor https://www.mujkaktus.cz/chces-pridat every 5 minutes
2. **Content Extraction**: Extract event title (e.g., "Dobíječka 9.9.2025 15:00 - 18:00") and description
3. **Date Parsing**: Parse Czech date format and convert to Prague timezone
4. **Duplicate Detection**: Use SHA256 hash to prevent re-processing the same post
5. **Immediate Notification**: Send full event details to all subscribers
6. **Smart Scheduling**: Queue reminder message for event start time using Telegram API

### Message Format

- **Immediate Notification**: Full event title + complete event description
- **Scheduled Reminder**: Brief reminder sent at event start time

### Technical Stack

- **Language**: Python 3.11+
- **Database**: PostgreSQL 15
- **Deployment**: Docker Compose
- **Key Libraries**: python-telegram-bot, BeautifulSoup4, SQLAlchemy, pytz

## Architecture

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    chat_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_started TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processed posts table
CREATE TABLE processed_posts (
    id SERIAL PRIMARY KEY,
    post_hash VARCHAR(64) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    event_datetime TIMESTAMP WITH TIME ZONE,
    notifications_sent BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Project Structure

```
kaktus-telegram-bot/
├── docker-compose.yml      # Local development
├── docker-compose.prod.yml # Production with GHCR image
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
├── src/
│   ├── main.py          # Application entry point
│   ├── bot.py           # Telegram bot handlers
│   ├── scraper.py       # Web scraping logic
│   ├── database.py      # Database models and operations
│   ├── config.py        # Configuration management
│   └── utils.py         # Utility functions (date parsing, etc.)
├── tests/              # Comprehensive test suite
├── logs/               # Application logs
└── templates/          # Test HTML templates
```

## Development

### Local Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up local PostgreSQL**
   ```bash
   # Using Docker
   docker run -d -p 5432:5432 \
     -e POSTGRES_DB=telegram_bot \
     -e POSTGRES_USER=bot \
     -e POSTGRES_PASSWORD=password \
     postgres:15-alpine
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and database URL
   ```

4. **Run the bot**
   ```bash
   python src/main.py
   ```

### Testing

#### Running Tests
```bash
# In Docker container
docker-compose exec bot python -m pytest

# Locally
python -m pytest tests/
```

#### Test Coverage
The test suite includes:
- Bot command handling (`/start`, `/stop`)
- Web scraping functionality
- Date parsing (Czech format)
- Database operations
- Duplicate detection
- Configuration management

#### Test Server
For testing notifications locally:
```bash
python test_server.py
# Visit http://localhost:8080/admin to modify test events
```

### Monitoring and Debugging

#### View Application Logs
```bash
# All services
docker-compose logs -f

# Bot only
docker-compose logs -f bot

# Database only
docker-compose logs -f db
```

#### Debug Scraper
```bash
python debug-scraper.py
```

## Deployment

### GitHub Container Registry

The container is automatically built and pushed to GHCR on every commit to main branch.

```bash
# Pull the latest image
docker pull ghcr.io/kulebyaka/kaktuscc:latest

# Or use the production compose file
docker-compose -f docker-compose.prod.yml up -d
```

### Production Deployment

1. **Server Requirements**
   - Linux VPS with Docker installed
   - Minimum 1GB RAM
   - Persistent storage for database

2. **Environment Setup**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export GITHUB_REPOSITORY="kulebyaka/kaktuscc"
   ```

3. **Deploy**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Troubleshooting

### Common Issues

#### Bot doesn't respond to commands
- ✅ Verify `TELEGRAM_BOT_TOKEN` is correct
- ✅ Check if bot is blocked by the user
- ✅ Review logs for error messages: `docker-compose logs -f bot`

#### Duplicate notifications sent
- ✅ Ensure `post_hash` calculation is consistent
- ✅ Check database connectivity
- ✅ Verify processed_posts table is being updated

#### Wrong notification times
- ✅ Verify timezone configuration (`TZ=Europe/Prague`)
- ✅ Check date parsing logic in logs
- ✅ Ensure Prague timezone conversion to UTC is correct

#### Database connection errors
- ✅ Ensure PostgreSQL container is running: `docker-compose ps`
- ✅ Verify `DATABASE_URL` format
- ✅ Check network connectivity between containers

#### Scheduled messages not sent
- ✅ Verify event datetime is in the future
- ✅ Check that datetime is within Telegram's limits (max 365 days)
- ✅ Ensure timezone conversion is accurate

### Rate Limiting

The bot respects Telegram's API limits:
- Maximum 30 messages per second to different users
- Uses async operations for efficiency
- Implements message batching for multiple subscribers
- Exponential backoff for network failures

### Data Persistence

- Database data persists in Docker volumes
- Logs are stored in the `logs/` directory
- Configuration is managed through environment variables

## Security Considerations

- ✅ Bot token must be kept secret (use environment variables)
- ✅ Database credentials in environment variables only
- ✅ No public database port exposure
- ✅ Read-only web scraping (no authentication needed)
- ✅ Input validation for user commands
- ✅ Proper error handling to prevent information leaks

## API Limitations

### Telegram Message Scheduling
- Uses `schedule_date` parameter (Unix timestamp)
- Maximum: 365 days in advance
- Minimum: 10 seconds in future
- Cannot modify or cancel once scheduled
- Prague timezone converted to UTC for API

### Date/Time Parsing Rules
- Pattern: `DD.MM.YYYY HH:MM - HH:MM`
- Example: `"Dobíječka 9.9.2025 15:00 - 18:00"`
- Extract start time only (first time occurrence)
- Always interpret in Prague timezone (`Europe/Prague`)
- Convert to UTC timestamp for Telegram API

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `python -m pytest`
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review application logs: `docker-compose logs -f bot`
3. Run the test suite: `python -m pytest tests/`
4. Open an issue on GitHub with detailed information

---

*This bot helps T-Mobile Kaktus users stay informed about promotional events and special offers through automated Telegram notifications.*