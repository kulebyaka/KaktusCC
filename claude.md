# CLAUDE.md - Kaktus Telegram Notification Bot

## Project Overview

This is a Telegram bot that monitors the T-Mobile Kaktus webpage (https://www.mujkaktus.cz/chces-pridat) for new promotional events and sends notifications to subscribed users. When a new event is posted, the bot sends an immediate notification and schedules a reminder for when the event starts.

## Core Functionality

### 1. Web Scraping
- Monitor https://www.mujkaktus.cz/chces-pridat for new posts
- Extract event title (e.g., "Dobíječka 9.9.2025 15:00 - 18:00")
- Extract event description/content
- Parse Czech date/time format from the title
- Check every 5 minutes for updates
- Use SHA256 hash to detect duplicate posts

### 2. Telegram Bot Features
- `/start` command - Subscribe user to notifications
- `/stop` command - Unsubscribe from notifications
- Send immediate notification when new event is detected
- Schedule automatic reminder using Telegram's `schedule_date` parameter
- Handle Prague timezone (Europe/Prague) correctly

### 3. Message Format
- **Immediate notification**: Full title + complete event description
- **Scheduled reminder**: Brief reminder sent at event start time

## Technical Stack

- **Language**: Python 3.11+
- **Database**: PostgreSQL 15
- **Deployment**: Docker Compose
- **VPS**: Linux-based server with Docker installed

### Key Python Libraries
- `python-telegram-bot==20.7` - Telegram Bot API wrapper
- `beautifulsoup4==4.12.2` - HTML parsing
- `requests==2.31.0` - HTTP requests
- `psycopg2-binary==2.9.9` - PostgreSQL adapter
- `SQLAlchemy==2.0.23` - ORM
- `pytz==2023.3` - Timezone handling
- `python-dotenv==1.0.0` - Environment variables

## Database Schema

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

## Project Structure

```
kaktus-telegram-bot/
├── docker-compose.yml      # Docker orchestration
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (not in git)
├── .env.example          # Example environment file
├── src/
│   ├── __init__.py
│   ├── main.py          # Application entry point
│   ├── bot.py           # Telegram bot handlers
│   ├── scraper.py       # Web scraping logic
│   ├── database.py      # Database models and operations
│   ├── config.py        # Configuration management
│   └── utils.py         # Utility functions (date parsing, etc.)
├── logs/                # Application logs
└── tests/              # Unit tests
```

## Environment Variables

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# Database Configuration  
DATABASE_URL=postgresql://bot:password@db:5432/telegram_bot

# Scraping Configuration
SCRAPE_URL=https://www.mujkaktus.cz/chces-pridat
CHECK_INTERVAL=300  # seconds (5 minutes)

# Application Configuration
LOG_LEVEL=INFO
TZ=Europe/Prague
```

## Date/Time Parsing Rules

The bot must parse Czech date format from titles:
- Pattern: `DD.MM.YYYY HH:MM - HH:MM`
- Example: `"Dobíječka 9.9.2025 15:00 - 18:00"`
- Extract start time only (first time occurrence)
- Always interpret in Prague timezone (Europe/Prague)
- Convert to UTC timestamp for Telegram API

## Error Handling Requirements

1. **Network Failures**: Retry with exponential backoff
2. **Telegram Rate Limits**: Implement message batching (max 30 msg/sec)
3. **Invalid Dates**: Skip scheduled message if date parsing fails
4. **User Blocks**: Mark user as inactive if bot is blocked
5. **Duplicate Posts**: Use hash comparison to prevent re-sending

## Telegram API Specifics

### Message Scheduling
- Use `schedule_date` parameter (Unix timestamp)
- Maximum: 365 days in advance
- Minimum: 10 seconds in future
- Cannot modify/cancel once scheduled

### Rate Limits
- 30 messages per second to different users
- Use async operations for efficiency
- Batch processing when sending to multiple users

## Deployment Notes

### Docker Compose Services
1. **bot**: Main Python application
   - Depends on database
   - Auto-restart policy
   - Volume mount for logs

2. **db**: PostgreSQL database
   - Alpine variant for smaller size
   - Persistent volume for data
   - Internal network only

### Security Considerations
- Bot token must be kept secret
- Database credentials in environment variables
- No public database port exposure
- Use read-only scraping (no authentication needed)

## Testing Checklist

- [ ] Bot responds to `/start` command
- [ ] User gets saved to database
- [ ] Webpage scraping extracts correct data
- [ ] Date parsing handles Czech format
- [ ] Duplicate detection works correctly
- [ ] Immediate notification sent to all users
- [ ] Scheduled message sent at correct time
- [ ] Timezone conversion is accurate
- [ ] Bot handles `/stop` command
- [ ] Database persists after container restart

## Common Issues & Solutions

### Issue: Scheduled messages sent at wrong time
**Solution**: Ensure Prague timezone is properly converted to UTC timestamp

### Issue: Duplicate notifications
**Solution**: Check post_hash is being calculated consistently

### Issue: Bot doesn't respond
**Solution**: Verify bot token and that bot is not blocked by user

### Issue: Memory leaks in long-running process
**Solution**: Use connection pooling for database, close requests sessions

## Future Enhancements (Not Implemented)

- Web dashboard for statistics
- User preferences (notification types)
- Multiple webpage monitoring
- Rich message formatting (photos, buttons)
- Admin commands for bot management
- Backup scheduled messages in database (fallback)