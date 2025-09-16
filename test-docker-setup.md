# Testing Docker Setup

## Quick Test Commands

### 1. Create .env file first
```bash
cp .env.example .env
```

Edit `.env` and add your actual Telegram bot token:
```
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
```

### 2. Build and run
```bash
# Clean build
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### 3. Watch logs
```bash
# In separate terminal
docker-compose logs -f bot
docker-compose logs -f db
```

### 4. Test database connectivity
```bash
# Connect to database container
docker-compose exec db psql -U bot -d telegram_bot

# Inside psql:
\dt  # List tables
SELECT * FROM users;
SELECT * FROM processed_posts;
\q   # Quit
```

### 5. Test bot commands
Send these messages to your bot in Telegram:
- `/start` - Should subscribe you
- `/stop` - Should unsubscribe you

## Expected Startup Sequence

1. **Database starts** and health check passes
2. **Bot waits** for database to be ready (up to 60 seconds)
3. **Database connection** established with retry logic
4. **Tables created** automatically
5. **Bot starts** and begins monitoring
6. **Logs show**: "Starting webpage monitoring every X seconds"

## Troubleshooting

### If database connection still fails:
1. Check `.env` file exists with correct `DATABASE_URL`
2. Verify Docker network connectivity:
   ```bash
   docker-compose exec bot ping db
   ```
3. Check database logs:
   ```bash
   docker-compose logs db
   ```

### If bot doesn't respond:
1. Verify `TELEGRAM_BOT_TOKEN` in `.env`
2. Check bot logs for errors:
   ```bash
   docker-compose logs bot
   ```
3. Ensure bot is not already used by another instance

### Clean restart:
```bash
docker-compose down -v  # Removes volumes too
docker-compose up --build
```

## Success Indicators

✅ **Database**: `database is ready` in logs  
✅ **Connection**: `Database connection successful`  
✅ **Tables**: `Database tables created successfully`  
✅ **Bot**: `Telegram bot started successfully`  
✅ **Monitoring**: `Starting webpage monitoring every 300 seconds`  

## Common Issues Fixed

- ❌ Connection refused → ✅ Health checks + retry logic
- ❌ Bot starts before DB → ✅ `depends_on` with health condition  
- ❌ Race conditions → ✅ Wait script + connection testing
- ❌ Network issues → ✅ Exponential backoff retry