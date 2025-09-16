import pytest
import asyncio
import signal
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.main import KaktusNotificationApp, main

class TestKaktusNotificationApp:
    
    @pytest.fixture
    def app(self):
        """Create KaktusNotificationApp instance for testing."""
        return KaktusNotificationApp()
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, app, temp_env):
        """Test successful application initialization."""
        with patch('src.main.DatabaseManager') as mock_db_manager, \
             patch('src.main.KaktusScraper') as mock_scraper, \
             patch('src.main.TelegramBot') as mock_bot, \
             patch.object(app.config, 'validate'), \
             patch.object(app.config, 'setup_logging'):
            
            mock_db_instance = Mock()
            mock_scraper_instance = Mock()
            mock_bot_instance = Mock()
            mock_bot_instance.start_bot = AsyncMock()
            
            mock_db_manager.return_value = mock_db_instance
            mock_scraper.return_value = mock_scraper_instance
            mock_bot.return_value = mock_bot_instance
            
            await app.initialize()
            
            app.config.validate.assert_called_once()
            app.config.setup_logging.assert_called_once()
            mock_db_instance.create_tables.assert_called_once()
            mock_bot_instance.start_bot.assert_called_once()
            
            assert app.db_manager == mock_db_instance
            assert app.scraper == mock_scraper_instance
            assert app.bot == mock_bot_instance
    
    @pytest.mark.asyncio
    async def test_initialize_config_validation_failure(self, app):
        """Test initialization failure due to config validation."""
        with patch.object(app.config, 'validate', side_effect=ValueError("Config error")):
            
            with pytest.raises(ValueError, match="Config error"):
                await app.initialize()
    
    @pytest.mark.asyncio
    async def test_initialize_database_error(self, app, temp_env):
        """Test initialization failure due to database error."""
        with patch('src.main.DatabaseManager') as mock_db_manager, \
             patch.object(app.config, 'validate'), \
             patch.object(app.config, 'setup_logging'):
            
            mock_db_instance = Mock()
            mock_db_instance.create_tables.side_effect = Exception("Database error")
            mock_db_manager.return_value = mock_db_instance
            
            with pytest.raises(Exception, match="Database error"):
                await app.initialize()
    
    @pytest.mark.asyncio
    async def test_initialize_bot_start_error(self, app, temp_env):
        """Test initialization failure due to bot start error."""
        with patch('src.main.DatabaseManager') as mock_db_manager, \
             patch('src.main.KaktusScraper') as mock_scraper, \
             patch('src.main.TelegramBot') as mock_bot, \
             patch.object(app.config, 'validate'), \
             patch.object(app.config, 'setup_logging'):
            
            mock_db_instance = Mock()
            mock_scraper_instance = Mock()
            mock_bot_instance = Mock()
            mock_bot_instance.start_bot = AsyncMock(side_effect=Exception("Bot start error"))
            
            mock_db_manager.return_value = mock_db_instance
            mock_scraper.return_value = mock_scraper_instance
            mock_bot.return_value = mock_bot_instance
            
            with pytest.raises(Exception, match="Bot start error"):
                await app.initialize()
    
    @pytest.mark.asyncio
    async def test_shutdown(self, app):
        """Test graceful application shutdown."""
        app.running = True
        app.bot = Mock()
        app.bot.stop_bot = AsyncMock()
        
        await app.shutdown()
        
        assert app.running is False
        app.bot.stop_bot.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_no_bot(self, app):
        """Test shutdown when bot is not initialized."""
        app.running = True
        app.bot = None
        
        await app.shutdown()
        
        assert app.running is False
    
    def test_setup_signal_handlers(self, app):
        """Test signal handler setup."""
        app.running = True
        
        with patch('signal.signal') as mock_signal:
            app.setup_signal_handlers()
            
            assert mock_signal.call_count == 2
            
            calls = mock_signal.call_args_list
            signal_nums = [call[0][0] for call in calls]
            assert signal.SIGINT in signal_nums
            assert signal.SIGTERM in signal_nums
    
    def test_signal_handler_functionality(self, app):
        """Test that signal handler sets running to False."""
        app.running = True
        app.setup_signal_handlers()
        
        import os
        os.kill(os.getpid(), signal.SIGINT)
        
    @pytest.mark.asyncio
    async def test_run_success(self, app, temp_env):
        """Test successful application run."""
        mock_scraper_task = AsyncMock()
        
        with patch.object(app, 'initialize', new_callable=AsyncMock) as mock_init, \
             patch.object(app, 'setup_signal_handlers'), \
             patch.object(app, 'shutdown', new_callable=AsyncMock) as mock_shutdown, \
             patch('asyncio.create_task', return_value=mock_scraper_task), \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            app.running = True
            
            async def stop_after_first_sleep():
                app.running = False
            
            mock_sleep.side_effect = stop_after_first_sleep
            mock_scraper_task.done.return_value = False
            mock_scraper_task.cancel = Mock()
            
            await app.run()
            
            mock_init.assert_called_once()
            mock_shutdown.assert_called_once()
            mock_scraper_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_scraper_task_fails_and_restarts(self, app, temp_env):
        """Test that scraper task is restarted when it fails."""
        failed_task = AsyncMock()
        failed_task.done.return_value = True
        failed_task.exception.return_value = Exception("Scraper failed")
        
        new_task = AsyncMock()
        new_task.done.return_value = False
        new_task.cancel = Mock()
        
        task_calls = [failed_task, new_task]
        
        with patch.object(app, 'initialize', new_callable=AsyncMock), \
             patch.object(app, 'setup_signal_handlers'), \
             patch.object(app, 'shutdown', new_callable=AsyncMock), \
             patch('asyncio.create_task', side_effect=task_calls), \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            app.scraper = Mock()
            app.scraper.start_monitoring = AsyncMock()
            app.bot = Mock()
            app.bot.handle_new_post = Mock()
            app.running = True
            
            call_count = 0
            async def stop_after_two_sleeps():
                nonlocal call_count
                call_count += 1
                if call_count >= 2:
                    app.running = False
            
            mock_sleep.side_effect = stop_after_two_sleeps
            
            await app.run()
            
            new_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_keyboard_interrupt(self, app, temp_env):
        """Test handling KeyboardInterrupt in run loop."""
        with patch.object(app, 'initialize', new_callable=AsyncMock), \
             patch.object(app, 'setup_signal_handlers'), \
             patch.object(app, 'shutdown', new_callable=AsyncMock) as mock_shutdown, \
             patch('asyncio.create_task') as mock_create_task, \
             patch('asyncio.sleep', side_effect=KeyboardInterrupt()):
            
            mock_task = AsyncMock()
            mock_task.cancel = Mock()
            mock_create_task.return_value = mock_task
            
            await app.run()
            
            mock_shutdown.assert_called_once()
            mock_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_unexpected_exception(self, app, temp_env):
        """Test handling unexpected exception in run loop."""
        with patch.object(app, 'initialize', new_callable=AsyncMock), \
             patch.object(app, 'setup_signal_handlers'), \
             patch.object(app, 'shutdown', new_callable=AsyncMock) as mock_shutdown, \
             patch('asyncio.create_task') as mock_create_task, \
             patch('asyncio.sleep', side_effect=Exception("Unexpected error")):
            
            mock_task = AsyncMock()
            mock_task.cancel = Mock()
            mock_create_task.return_value = mock_task
            
            await app.run()
            
            mock_shutdown.assert_called_once()
            mock_task.cancel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_scraper_task_cancelled(self, app, temp_env):
        """Test handling cancelled scraper task during shutdown."""
        with patch.object(app, 'initialize', new_callable=AsyncMock), \
             patch.object(app, 'setup_signal_handlers'), \
             patch.object(app, 'shutdown', new_callable=AsyncMock), \
             patch('asyncio.create_task') as mock_create_task, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            mock_task = AsyncMock()
            mock_task.cancel = Mock()
            mock_task.done.return_value = False
            
            async def cancel_task_on_await():
                raise asyncio.CancelledError()
            
            mock_task.__aenter__ = AsyncMock(side_effect=cancel_task_on_await)
            mock_create_task.return_value = mock_task
            
            app.running = True
            
            async def stop_after_first_sleep():
                app.running = False
            
            mock_sleep.side_effect = stop_after_first_sleep
            
            await app.run()
            
            mock_task.cancel.assert_called_once()

class TestMainFunction:
    
    @pytest.mark.asyncio
    async def test_main_success(self, temp_env):
        """Test successful main function execution."""
        with patch('src.main.KaktusNotificationApp') as mock_app_class:
            mock_app = Mock()
            mock_app.run = AsyncMock()
            mock_app_class.return_value = mock_app
            
            await main()
            
            mock_app.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_application_failure(self):
        """Test main function handling application failure."""
        with patch('src.main.KaktusNotificationApp') as mock_app_class, \
             patch('sys.exit') as mock_exit:
            
            mock_app = Mock()
            mock_app.run = AsyncMock(side_effect=Exception("App failed"))
            mock_app_class.return_value = mock_app
            
            await main()
            
            mock_exit.assert_called_once_with(1)

class TestIntegrationScenarios:
    
    @pytest.mark.asyncio
    async def test_full_application_lifecycle(self, temp_env):
        """Test full application lifecycle integration."""
        app = KaktusNotificationApp()
        
        with patch('src.main.DatabaseManager') as mock_db_manager, \
             patch('src.main.KaktusScraper') as mock_scraper, \
             patch('src.main.TelegramBot') as mock_bot, \
             patch.object(app.config, 'validate'), \
             patch.object(app.config, 'setup_logging'), \
             patch('asyncio.create_task') as mock_create_task, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            mock_db_instance = Mock()
            mock_scraper_instance = Mock()
            mock_bot_instance = Mock()
            mock_bot_instance.start_bot = AsyncMock()
            mock_bot_instance.stop_bot = AsyncMock()
            
            mock_db_manager.return_value = mock_db_instance
            mock_scraper.return_value = mock_scraper_instance
            mock_bot.return_value = mock_bot_instance
            
            mock_task = AsyncMock()
            mock_task.done.return_value = False
            mock_task.cancel = Mock()
            mock_create_task.return_value = mock_task
            
            app.running = True
            
            async def stop_after_init():
                app.running = False
            
            mock_sleep.side_effect = stop_after_init
            
            await app.run()
            
            mock_db_instance.create_tables.assert_called_once()
            mock_bot_instance.start_bot.assert_called_once()
            mock_bot_instance.stop_bot.assert_called_once()
    
    @pytest.mark.asyncio 
    async def test_component_interaction_flow(self, temp_env):
        """Test that components interact correctly during normal flow."""
        app = KaktusNotificationApp()
        
        with patch('src.main.DatabaseManager') as mock_db_manager, \
             patch('src.main.KaktusScraper') as mock_scraper, \
             patch('src.main.TelegramBot') as mock_bot, \
             patch.object(app.config, 'validate'), \
             patch.object(app.config, 'setup_logging'):
            
            mock_db_instance = Mock()
            mock_scraper_instance = Mock()
            mock_bot_instance = Mock()
            mock_bot_instance.start_bot = AsyncMock()
            mock_bot_instance.handle_new_post = Mock()
            
            mock_db_manager.return_value = mock_db_instance
            mock_scraper.return_value = mock_scraper_instance
            mock_bot.return_value = mock_bot_instance
            
            await app.initialize()
            
            mock_scraper.assert_called_once_with(
                app.config.SCRAPE_URL,
                mock_db_instance,
                app.config.CHECK_INTERVAL
            )
            
            mock_bot.assert_called_once_with(
                app.config.TELEGRAM_BOT_TOKEN,
                mock_db_instance
            )
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, temp_env):
        """Test application recovery from various error scenarios."""
        app = KaktusNotificationApp()
        
        with patch.object(app, 'initialize', new_callable=AsyncMock) as mock_init, \
             patch.object(app, 'setup_signal_handlers'), \
             patch.object(app, 'shutdown', new_callable=AsyncMock), \
             patch('asyncio.create_task') as mock_create_task, \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            app.scraper = Mock()
            app.scraper.start_monitoring = AsyncMock()
            app.bot = Mock()
            app.bot.handle_new_post = Mock()
            
            failed_task1 = AsyncMock()
            failed_task1.done.return_value = True
            failed_task1.exception.return_value = Exception("First failure")
            
            failed_task2 = AsyncMock() 
            failed_task2.done.return_value = True
            failed_task2.exception.return_value = Exception("Second failure")
            
            final_task = AsyncMock()
            final_task.done.return_value = False
            final_task.cancel = Mock()
            
            mock_create_task.side_effect = [failed_task1, failed_task2, final_task]
            
            app.running = True
            call_count = 0
            
            async def stop_after_recovery():
                nonlocal call_count
                call_count += 1
                if call_count >= 3:
                    app.running = False
            
            mock_sleep.side_effect = stop_after_recovery
            
            await app.run()
            
            assert mock_create_task.call_count == 3
            final_task.cancel.assert_called_once()