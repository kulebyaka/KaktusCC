import pytest
from datetime import datetime
import pytz
from unittest.mock import patch
from src.utils import (
    parse_czech_datetime,
    calculate_post_hash,
    datetime_to_unix_timestamp,
    is_valid_schedule_time
)

class TestParseCzechDatetime:
    
    def test_parse_czech_datetime_valid_format(self):
        """Test parsing valid Czech datetime format."""
        title = "Dobíječka 9.9.2025 15:00 - 18:00"
        result = parse_czech_datetime(title)
        
        assert result is not None
        assert result.year == 2025
        assert result.month == 9
        assert result.day == 9
        assert result.hour == 15
        assert result.minute == 0
        assert result.tzinfo.zone == 'Europe/Prague'
    
    def test_parse_czech_datetime_different_format(self):
        """Test parsing different valid format."""
        title = "Test event 15.12.2025 09:30 - 12:00"
        result = parse_czech_datetime(title)
        
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 15
        assert result.hour == 9
        assert result.minute == 30
    
    def test_parse_czech_datetime_single_digit_day_month(self):
        """Test parsing with single digit day and month."""
        title = "Event 5.3.2025 08:15 - 10:00"
        result = parse_czech_datetime(title)
        
        assert result is not None
        assert result.day == 5
        assert result.month == 3
        assert result.hour == 8
        assert result.minute == 15
    
    def test_parse_czech_datetime_invalid_format(self):
        """Test parsing invalid datetime format."""
        title = "Invalid date format"
        result = parse_czech_datetime(title)
        
        assert result is None
    
    def test_parse_czech_datetime_american_format(self):
        """Test that American format is not parsed."""
        title = "Event 03/05/2025 15:00 - 18:00"
        result = parse_czech_datetime(title)
        
        assert result is None
    
    def test_parse_czech_datetime_invalid_date_values(self):
        """Test parsing with invalid date values."""
        title = "Event 32.13.2025 25:70 - 18:00"
        result = parse_czech_datetime(title)
        
        assert result is None
    
    def test_parse_czech_datetime_custom_timezone(self):
        """Test parsing with custom timezone."""
        title = "Event 10.10.2025 14:30 - 17:00"
        result = parse_czech_datetime(title, 'UTC')
        
        assert result is not None
        assert result.tzinfo.zone == 'UTC'

class TestCalculatePostHash:
    
    def test_calculate_post_hash_same_content(self):
        """Test that same content produces same hash."""
        title = "Test Title"
        content = "Test Content"
        
        hash1 = calculate_post_hash(title, content)
        hash2 = calculate_post_hash(title, content)
        
        assert hash1 == hash2
        assert len(hash1) == 64
    
    def test_calculate_post_hash_different_content(self):
        """Test that different content produces different hash."""
        hash1 = calculate_post_hash("Title 1", "Content 1")
        hash2 = calculate_post_hash("Title 2", "Content 2")
        
        assert hash1 != hash2
    
    def test_calculate_post_hash_strips_whitespace(self):
        """Test that whitespace is stripped before hashing."""
        hash1 = calculate_post_hash("  Title  ", "  Content  ")
        hash2 = calculate_post_hash("Title", "Content")
        
        assert hash1 == hash2
    
    def test_calculate_post_hash_unicode_content(self):
        """Test hashing with unicode content."""
        title = "Nabíjení 🔋"
        content = "Speciální akce s emoji"
        
        hash_result = calculate_post_hash(title, content)
        
        assert len(hash_result) == 64
        assert isinstance(hash_result, str)

class TestDatetimeToUnixTimestamp:
    
    def test_datetime_to_unix_timestamp_with_timezone(self):
        """Test conversion with timezone-aware datetime."""
        prague_tz = pytz.timezone('Europe/Prague')
        dt = prague_tz.localize(datetime(2025, 9, 9, 15, 0))
        
        timestamp = datetime_to_unix_timestamp(dt)
        
        assert isinstance(timestamp, int)
        assert timestamp > 0
    
    def test_datetime_to_unix_timestamp_naive_datetime(self):
        """Test conversion with naive datetime (assumes UTC)."""
        dt = datetime(2025, 9, 9, 15, 0)
        
        with patch('src.utils.logger') as mock_logger:
            timestamp = datetime_to_unix_timestamp(dt)
            
            mock_logger.warning.assert_called_once()
            assert isinstance(timestamp, int)
    
    def test_datetime_to_unix_timestamp_utc_datetime(self):
        """Test conversion with UTC datetime."""
        dt = pytz.UTC.localize(datetime(2025, 9, 9, 15, 0))
        
        timestamp = datetime_to_unix_timestamp(dt)
        expected = int(dt.timestamp())
        
        assert timestamp == expected

class TestIsValidScheduleTime:
    
    def test_is_valid_schedule_time_future_valid(self):
        """Test valid future time for scheduling."""
        now = datetime.now(pytz.UTC)
        future_time = now.replace(hour=now.hour + 1)
        
        result = is_valid_schedule_time(future_time)
        
        assert result is True
    
    def test_is_valid_schedule_time_too_soon(self):
        """Test time too soon for scheduling (less than 10 seconds)."""
        now = datetime.now(pytz.UTC)
        
        result = is_valid_schedule_time(now)
        
        assert result is False
    
    def test_is_valid_schedule_time_too_far(self):
        """Test time too far in future (more than 365 days)."""
        now = datetime.now(pytz.UTC)
        far_future = now.replace(year=now.year + 2)
        
        result = is_valid_schedule_time(far_future)
        
        assert result is False
    
    def test_is_valid_schedule_time_past_time(self):
        """Test past time is not valid."""
        now = datetime.now(pytz.UTC)
        past_time = now.replace(hour=now.hour - 1)
        
        result = is_valid_schedule_time(past_time)
        
        assert result is False
    
    def test_is_valid_schedule_time_naive_datetime(self):
        """Test naive datetime is handled correctly."""
        future_naive = datetime(2025, 12, 31, 15, 0)
        
        result = is_valid_schedule_time(future_naive)
        
        assert isinstance(result, bool)
    
    def test_is_valid_schedule_time_different_timezone(self):
        """Test datetime with different timezone."""
        prague_tz = pytz.timezone('Europe/Prague')
        future_prague = prague_tz.localize(datetime(2025, 12, 31, 15, 0))
        
        result = is_valid_schedule_time(future_prague)
        
        assert isinstance(result, bool)