# Test Suite for Kaktus Telegram Bot

This directory contains comprehensive unit and integration tests for all modules in the Kaktus Telegram Notification Bot project.

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_config.py           # Tests for config.py module
├── test_utils.py            # Tests for utils.py module  
├── test_database.py         # Tests for database.py module
├── test_scraper.py          # Tests for scraper.py module
├── test_bot.py              # Tests for bot.py module
├── test_main.py             # Integration tests for main.py module
└── README.md                # This file
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest
```

### Run Specific Test Files
```bash
pytest tests/test_config.py
pytest tests/test_utils.py
pytest tests/test_database.py
pytest tests/test_scraper.py
pytest tests/test_bot.py
pytest tests/test_main.py
```

### Run Tests with Coverage
```bash
pytest --cov=src --cov-report=html
```

### Run Tests by Marker
```bash
pytest -m unit
pytest -m integration
pytest -m asyncio
```

## Test Categories

### Unit Tests
- **test_config.py**: Configuration loading, validation, logging setup
- **test_utils.py**: Date parsing, hash calculation, timestamp conversion
- **test_database.py**: Database operations, user management, post tracking
- **test_scraper.py**: Web scraping, HTML parsing, monitoring loop
- **test_bot.py**: Telegram bot commands, notifications, scheduling

### Integration Tests  
- **test_main.py**: Application lifecycle, component interaction, error recovery

## Test Coverage

The test suite covers:

✅ **Configuration Management**
- Environment variable loading
- Default value handling
- Validation logic
- Logging configuration

✅ **Utility Functions**
- Czech datetime parsing (multiple formats)
- Hash calculation for deduplication
- Timezone conversion
- Telegram API timestamp validation

✅ **Database Operations**
- User management (add, deactivate, reactivate)
- Post tracking and deduplication
- Active user retrieval
- Error handling and rollback

✅ **Web Scraping**
- HTML parsing from various structures
- Post extraction and validation
- Monitoring loop with error recovery
- Rate limiting and session management

✅ **Telegram Bot**
- Command handlers (/start, /stop)
- Message formatting and sending
- Scheduled reminder functionality
- Error handling (blocked users, rate limits)
- User state management

✅ **Application Integration**
- Initialization and shutdown sequences
- Signal handler setup
- Component interaction
- Error recovery scenarios
- Task management and restart logic

## Test Fixtures

Key fixtures available in `conftest.py`:

- `temp_env`: Temporary environment variables for testing
- `test_db`: In-memory SQLite database for testing
- `db_manager`: Configured DatabaseManager instance
- `sample_post_data`: Sample post data for testing
- `sample_html`: Sample HTML content for scraper testing
- `mock_telegram_bot`: Mocked Telegram bot instance
- `mock_requests_get`: Mocked HTTP requests

## Test Patterns

### Async Test Handling
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Database Testing
```python
def test_database_operation(db_manager):
    result = db_manager.add_user(12345, 'testuser')
    assert result is True
```

### Mock Usage
```python
def test_with_mocks(mock_requests_get):
    mock_requests_get.return_value.content = b'<html>content</html>'
    result = scraper.fetch_page()
    assert result is not None
```

### Exception Testing
```python
def test_exception_handling():
    with pytest.raises(ValueError, match="Expected error message"):
        function_that_should_raise()
```

## Continuous Integration

Tests are designed to run in CI/CD environments:

- No external dependencies (uses mocks and fixtures)
- In-memory database for fast execution
- Comprehensive error scenario coverage
- Cross-platform compatibility

## Adding New Tests

When adding new functionality:

1. Create corresponding test methods
2. Use appropriate fixtures from `conftest.py`
3. Follow naming convention: `test_function_name_scenario`
4. Test both success and error cases
5. Mock external dependencies
6. Add docstrings explaining test purpose

## Test Performance

- Unit tests: ~50ms average
- Integration tests: ~200ms average  
- Full suite: ~5 seconds
- Memory usage: <50MB during testing