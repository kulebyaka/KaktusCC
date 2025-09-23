# Kaktus Telegram Notification Bot

A Telegram bot that monitors the T-Mobile Kaktus webpage for new promotional events and sends automated notifications to subscribed users. When a new event is posted, the bot sends an immediate notification and schedules a reminder for when the event starts.

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

#### Test Server
For testing notifications locally:
```bash
python test_server.py
# Visit http://localhost:8080/admin to modify test events
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

## API Limitations

### Telegram Message Scheduling
- Uses `schedule_date` parameter (Unix timestamp)
- Maximum: 365 days in advance
- Minimum: 10 seconds in future
- Cannot modify or cancel once scheduled
- Prague timezone converted to UTC for API

---

*This bot helps T-Mobile Kaktus users stay informed about promotional events and special offers through automated Telegram notifications.*
