import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import pytz
from telegram import Update, User as TelegramUser, Chat, Message
from telegram.error import Forbidden, BadRequest

from src.bot import TelegramBot
from src.database import DatabaseManager

class TestTelegramBot:
    
    @pytest.fixture
    def bot(self, db_manager):
        """Create TelegramBot instance for testing."""
        return TelegramBot('test_token_123', db_manager)
    
    def test_bot_initialization(self, bot, db_manager):
        """Test bot initialization."""
        assert bot.token == 'test_token_123'
        assert bot.db_manager == db_manager
        assert bot.application is not None
    
    def test_setup_handlers(self, bot):
        """Test that command handlers are set up."""
        handlers = bot.application.handlers
        
        assert len(handlers[0]) == 2
        handler_commands = [h.command[0] for h in handlers[0]]
        assert 'start' in handler_commands
        assert 'stop' in handler_commands

class TestBotCommands:
    
    @pytest.fixture
    def bot(self, db_manager):
        return TelegramBot('test_token_123', db_manager)
    
    @pytest.fixture
    def mock_update(self):
        """Create mock Update object."""
        update = Mock(spec=Update)
        update.effective_chat = Mock()
        update.effective_chat.id = 12345
        update.effective_user = Mock(spec=TelegramUser)
        update.effective_user.username = 'testuser'
        update.message = Mock(spec=Message)
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context."""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_start_command_new_user(self, bot, mock_update, mock_context):
        """Test /start command for new user."""
        with patch.object(bot.db_manager, 'add_user', return_value=True):
            await bot.start_command(mock_update, mock_context)
            
            bot.db_manager.add_user.assert_called_once_with(12345, 'testuser')
            mock_update.message.reply_text.assert_called_once()
            
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Vítejte u Kaktus" in call_args
            assert "Budete dostávat oznámení" in call_args
    
    @pytest.mark.asyncio
    async def test_start_command_existing_user(self, bot, mock_update, mock_context):
        """Test /start command for existing user."""
        with patch.object(bot.db_manager, 'add_user', return_value=False):
            await bot.start_command(mock_update, mock_context)
            
            bot.db_manager.add_user.assert_called_once_with(12345, 'testuser')
            mock_update.message.reply_text.assert_called_once()
            
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "již přihlášeni" in call_args
    
    @pytest.mark.asyncio
    async def test_start_command_no_username(self, bot, mock_update, mock_context):
        """Test /start command when user has no username."""
        mock_update.effective_user.username = None
        
        with patch.object(bot.db_manager, 'add_user', return_value=True):
            await bot.start_command(mock_update, mock_context)
            
            bot.db_manager.add_user.assert_called_once_with(12345, None)
    
    @pytest.mark.asyncio
    async def test_start_command_exception(self, bot, mock_update, mock_context):
        """Test /start command when reply fails."""
        mock_update.message.reply_text.side_effect = Exception("Send error")
        
        with patch.object(bot.db_manager, 'add_user', return_value=True):
            await bot.start_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_command_success(self, bot, mock_update, mock_context):
        """Test /stop command successful deactivation."""
        with patch.object(bot.db_manager, 'deactivate_user', return_value=True):
            await bot.stop_command(mock_update, mock_context)
            
            bot.db_manager.deactivate_user.assert_called_once_with(12345)
            mock_update.message.reply_text.assert_called_once()
            
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Odběr oznámení byl ukončen" in call_args
    
    @pytest.mark.asyncio
    async def test_stop_command_failure(self, bot, mock_update, mock_context):
        """Test /stop command deactivation failure."""
        with patch.object(bot.db_manager, 'deactivate_user', return_value=False):
            await bot.stop_command(mock_update, mock_context)
            
            bot.db_manager.deactivate_user.assert_called_once_with(12345)
            mock_update.message.reply_text.assert_called_once()
            
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Chyba při ukončování" in call_args
    
    @pytest.mark.asyncio
    async def test_stop_command_exception(self, bot, mock_update, mock_context):
        """Test /stop command when reply fails."""
        mock_update.message.reply_text.side_effect = Exception("Send error")
        
        with patch.object(bot.db_manager, 'deactivate_user', return_value=True):
            await bot.stop_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()

class TestBotNotifications:
    
    @pytest.fixture
    def bot(self, db_manager):
        return TelegramBot('test_token_123', db_manager)
    
    @pytest.mark.asyncio
    async def test_send_immediate_notification_success(self, bot, sample_post_data):
        """Test sending immediate notification to active users."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[12345, 67890]), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            await bot.send_immediate_notification(sample_post_data)
            
            assert mock_send.call_count == 2
            
            for call in mock_send.call_args_list:
                args, kwargs = call
                assert kwargs['parse_mode'] == 'Markdown'
                assert 'Nová Kaktus akce!' in kwargs['text']
                assert sample_post_data['title'] in kwargs['text']
                assert sample_post_data['content'] in kwargs['text']
    
    @pytest.mark.asyncio
    async def test_send_immediate_notification_no_users(self, bot, sample_post_data):
        """Test sending notification when no active users."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[]), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            await bot.send_immediate_notification(sample_post_data)
            
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_immediate_notification_forbidden_error(self, bot, sample_post_data):
        """Test handling Forbidden error (bot blocked by user)."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[12345]), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send, \
             patch.object(bot.db_manager, 'mark_user_inactive_on_block') as mock_mark_inactive:
            
            mock_send.side_effect = Forbidden("Bot was blocked")
            
            await bot.send_immediate_notification(sample_post_data)
            
            mock_mark_inactive.assert_called_once_with(12345)
    
    @pytest.mark.asyncio
    async def test_send_immediate_notification_bad_request(self, bot, sample_post_data):
        """Test handling BadRequest error."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[12345]), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            mock_send.side_effect = BadRequest("Bad request")
            
            await bot.send_immediate_notification(sample_post_data)
            
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_immediate_notification_generic_exception(self, bot, sample_post_data):
        """Test handling generic exception."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[12345]), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            mock_send.side_effect = Exception("Generic error")
            
            await bot.send_immediate_notification(sample_post_data)
            
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_immediate_notification_rate_limiting(self, bot, sample_post_data):
        """Test rate limiting between messages."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[1, 2, 3]), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock), \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            await bot.send_immediate_notification(sample_post_data)
            
            assert mock_sleep.call_count == 3
            for call in mock_sleep.call_args_list:
                assert call[0][0] == 0.05

class TestBotScheduledReminders:
    
    @pytest.fixture
    def bot(self, db_manager):
        return TelegramBot('test_token_123', db_manager)
    
    @pytest.mark.asyncio
    async def test_schedule_reminder_success(self, bot, sample_post_data):
        """Test scheduling reminder for valid future time."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[12345]), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send, \
             patch('src.bot.is_valid_schedule_time', return_value=True), \
             patch('src.bot.datetime_to_unix_timestamp', return_value=1234567890):
            
            await bot.schedule_reminder(sample_post_data)
            
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            assert kwargs['schedule_date'] == 1234567890
            assert 'Připomínka' in kwargs['text']
    
    @pytest.mark.asyncio
    async def test_schedule_reminder_no_event_datetime(self, bot, sample_post_data):
        """Test scheduling when no event datetime is provided."""
        sample_post_data['event_datetime'] = None
        
        with patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            await bot.schedule_reminder(sample_post_data)
            
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_schedule_reminder_invalid_time(self, bot, sample_post_data):
        """Test scheduling when event time is not valid."""
        with patch('src.bot.is_valid_schedule_time', return_value=False), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            await bot.schedule_reminder(sample_post_data)
            
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_schedule_reminder_no_users(self, bot, sample_post_data):
        """Test scheduling when no active users."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[]), \
             patch('src.bot.is_valid_schedule_time', return_value=True), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            await bot.schedule_reminder(sample_post_data)
            
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_schedule_reminder_exception(self, bot, sample_post_data):
        """Test handling exception during scheduling."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[12345]), \
             patch('src.bot.is_valid_schedule_time', return_value=True), \
             patch('src.bot.datetime_to_unix_timestamp', return_value=1234567890), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock) as mock_send:
            
            mock_send.side_effect = Exception("Scheduling error")
            
            await bot.schedule_reminder(sample_post_data)
            
            mock_send.assert_called_once()

class TestBotPostHandling:
    
    @pytest.fixture
    def bot(self, db_manager):
        return TelegramBot('test_token_123', db_manager)
    
    @pytest.mark.asyncio
    async def test_handle_new_post(self, bot, sample_post_data):
        """Test handling new post (sends notification and schedules reminder)."""
        with patch.object(bot, 'send_immediate_notification', new_callable=AsyncMock) as mock_notify, \
             patch.object(bot, 'schedule_reminder', new_callable=AsyncMock) as mock_schedule:
            
            await bot.handle_new_post(sample_post_data)
            
            mock_notify.assert_called_once_with(sample_post_data)
            mock_schedule.assert_called_once_with(sample_post_data)

class TestBotLifecycle:
    
    @pytest.fixture
    def bot(self, db_manager):
        return TelegramBot('test_token_123', db_manager)
    
    @pytest.mark.asyncio
    async def test_start_bot(self, bot):
        """Test starting the bot."""
        with patch.object(bot.application, 'initialize', new_callable=AsyncMock) as mock_init, \
             patch.object(bot.application, 'start', new_callable=AsyncMock) as mock_start:
            
            await bot.start_bot()
            
            mock_init.assert_called_once()
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_bot(self, bot):
        """Test stopping the bot."""
        with patch.object(bot.application, 'stop', new_callable=AsyncMock) as mock_stop, \
             patch.object(bot.application, 'shutdown', new_callable=AsyncMock) as mock_shutdown:
            
            await bot.stop_bot()
            
            mock_stop.assert_called_once()
            mock_shutdown.assert_called_once()
    
    def test_run_polling(self, bot):
        """Test running bot in polling mode."""
        with patch.object(bot.application, 'run_polling') as mock_polling:
            
            bot.run_polling()
            
            mock_polling.assert_called_once()

class TestBotEdgeCases:
    
    @pytest.fixture
    def bot(self, db_manager):
        return TelegramBot('test_token_123', db_manager)
    
    @pytest.mark.asyncio
    async def test_send_notification_mixed_success_failure(self, bot, sample_post_data):
        """Test sending notifications with mixed success/failure."""
        def mock_send_message(chat_id, **kwargs):
            if chat_id == 12345:
                return AsyncMock()
            elif chat_id == 67890:
                raise Forbidden("Bot blocked")
            else:
                raise Exception("Generic error")
        
        with patch.object(bot.db_manager, 'get_active_users', return_value=[12345, 67890, 11111]), \
             patch.object(bot.application.bot, 'send_message', side_effect=mock_send_message), \
             patch.object(bot.db_manager, 'mark_user_inactive_on_block') as mock_mark_inactive, \
             patch('asyncio.sleep', new_callable=AsyncMock):
            
            await bot.send_immediate_notification(sample_post_data)
            
            mock_mark_inactive.assert_called_once_with(67890)
    
    @pytest.mark.asyncio
    async def test_schedule_reminder_rate_limiting(self, bot, sample_post_data):
        """Test rate limiting in scheduled reminders."""
        with patch.object(bot.db_manager, 'get_active_users', return_value=[1, 2, 3]), \
             patch('src.bot.is_valid_schedule_time', return_value=True), \
             patch('src.bot.datetime_to_unix_timestamp', return_value=1234567890), \
             patch.object(bot.application.bot, 'send_message', new_callable=AsyncMock), \
             patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            
            await bot.schedule_reminder(sample_post_data)
            
            assert mock_sleep.call_count == 3
            for call in mock_sleep.call_args_list:
                assert call[0][0] == 0.05