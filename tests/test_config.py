import pytest
import os
import logging
from unittest.mock import patch, MagicMock
from src.config import Config

class TestConfig:
    
    def test_config_loads_environment_variables(self, temp_env):
        """Test that Config loads environment variables correctly."""
        assert Config.TELEGRAM_BOT_TOKEN == 'test_token_123'
        assert Config.DATABASE_URL == 'sqlite:///:memory:'
        assert Config.SCRAPE_URL == 'https://test.example.com'
        assert Config.CHECK_INTERVAL == 60
        assert Config.LOG_LEVEL == 'DEBUG'
        assert Config.TZ == 'Europe/Prague'
    
    def test_config_default_values(self):
        """Test that Config uses default values when env vars are not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to get fresh values
            from importlib import reload
            import src.config
            reload(src.config)
            
            assert src.config.Config.SCRAPE_URL == 'https://www.mujkaktus.cz/chces-pridat'
            assert src.config.Config.CHECK_INTERVAL == 300
            assert src.config.Config.LOG_LEVEL == 'INFO'
            assert src.config.Config.TZ == 'Europe/Prague'
    
    def test_validate_success(self, temp_env):
        """Test that validate() passes with required environment variables."""
        Config.validate()
    
    def test_validate_missing_telegram_token(self):
        """Test that validate() raises error when TELEGRAM_BOT_TOKEN is missing."""
        with patch.dict(os.environ, {'DATABASE_URL': 'test_db'}, clear=True):
            from importlib import reload
            import src.config
            reload(src.config)
            
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is required"):
                src.config.Config.validate()
    
    def test_validate_missing_database_url(self):
        """Test that validate() raises error when DATABASE_URL is missing."""
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test_token'}, clear=True):
            from importlib import reload
            import src.config
            reload(src.config)
            
            with pytest.raises(ValueError, match="DATABASE_URL is required"):
                src.config.Config.validate()
    
    @patch('logging.basicConfig')
    @patch('logging.FileHandler')
    @patch('logging.StreamHandler')
    def test_setup_logging(self, mock_stream_handler, mock_file_handler, mock_basic_config, temp_env):
        """Test that setup_logging() configures logging correctly."""
        mock_file_handler_instance = MagicMock()
        mock_stream_handler_instance = MagicMock()
        mock_file_handler.return_value = mock_file_handler_instance
        mock_stream_handler.return_value = mock_stream_handler_instance
        
        Config.setup_logging()
        
        mock_file_handler.assert_called_once_with('logs/bot.log')
        mock_stream_handler.assert_called_once()
        
        mock_basic_config.assert_called_once_with(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[mock_file_handler_instance, mock_stream_handler_instance]
        )
    
    def test_check_interval_type_conversion(self):
        """Test that CHECK_INTERVAL is converted to integer."""
        with patch.dict(os.environ, {'CHECK_INTERVAL': '120'}, clear=True):
            from importlib import reload
            import src.config
            reload(src.config)
            
            assert src.config.Config.CHECK_INTERVAL == 120
            assert isinstance(src.config.Config.CHECK_INTERVAL, int)