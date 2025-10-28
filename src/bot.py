from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import Forbidden, BadRequest, NetworkError, TimedOut
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import asyncio
from .database import DatabaseManager
from .utils import datetime_to_unix_timestamp, is_valid_schedule_time, escape_markdown

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, db_manager: DatabaseManager):
        self.token = token
        self.db_manager = db_manager
        self.application = Application.builder().token(token).build()
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Setup command handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))

    async def _send_message_with_retry(
        self,
        chat_id: int,
        message: str,
        parse_mode: str = 'MarkdownV2',
        max_retries: int = 4,
        bot = None
    ) -> bool:
        """
        Send a message with exponential backoff retry logic for network errors.

        Args:
            chat_id: Telegram chat ID
            message: Message text to send
            parse_mode: Message parse mode (default: MarkdownV2)
            max_retries: Maximum number of retry attempts (default: 4)
            bot: Bot instance to use (default: self.application.bot)

        Returns:
            True if message sent successfully, False otherwise
        """
        if bot is None:
            bot = self.application.bot

        retry_delays = [2, 4, 8, 16]  # Exponential backoff in seconds

        for attempt in range(max_retries + 1):
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
                return True

            except Forbidden:
                # User blocked the bot - don't retry
                logger.warning(f"Bot blocked by user {chat_id}, marking as inactive")
                self.db_manager.mark_user_inactive_on_block(chat_id)
                return False

            except BadRequest as e:
                # Bad request - don't retry (likely invalid message format)
                logger.error(f"Bad request when sending to {chat_id}: {e}")
                return False

            except (NetworkError, TimedOut) as e:
                # Network errors are retryable with exponential backoff
                # Note: BadRequest is a subclass of NetworkError in telegram library,
                # so it must be caught before this block
                if attempt < max_retries:
                    delay = retry_delays[attempt]
                    logger.warning(
                        f"Network error sending to {chat_id} (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Failed to send message to {chat_id} after {max_retries + 1} attempts due to network error: {e}"
                    )
                    return False

            except Exception as e:
                # Other unexpected errors - don't retry
                logger.error(f"Unexpected error sending message to {chat_id}: {e}")
                return False

        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        chat_id = update.effective_chat.id
        username = update.effective_user.username if update.effective_user else None
        
        success = self.db_manager.add_user(chat_id, username)
        
        if success:
            welcome_message = (
                "🌵 Vítejte u Kaktus notifikačního botu!\n\n"
                "Budete dostávat oznámení o nových akcích na T-Mobile Kaktus.\n"
                "Pro ukončení odběru použijte /stop"
            )
        else:
            welcome_message = (
                "🌵 Jste již přihlášeni k odběru oznámení!\n\n"
                "Pro ukončení odběru použijte /stop"
            )
        
        try:
            await update.message.reply_text(welcome_message)
            logger.info(f"Start command processed for user {chat_id}")
        except Exception as e:
            logger.error(f"Error sending start message to {chat_id}: {e}")
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command."""
        chat_id = update.effective_chat.id
        
        success = self.db_manager.deactivate_user(chat_id)
        
        if success:
            goodbye_message = (
                "👋 Odběr oznámení byl ukončen.\n\n"
                "Pro obnovení odběru použijte /start"
            )
        else:
            goodbye_message = "❌ Chyba při ukončování odběru."
        
        try:
            await update.message.reply_text(goodbye_message)
            logger.info(f"Stop command processed for user {chat_id}")
        except Exception as e:
            logger.error(f"Error sending stop message to {chat_id}: {e}")
    
    async def send_immediate_notification(self, post_data: Dict[str, Any]):
        """Send immediate notification to all active users with retry logic for network errors."""
        active_users = self.db_manager.get_active_users()

        if not active_users:
            logger.info("No active users to notify")
            return

        # Escape title and content to prevent Markdown parsing errors
        escaped_title = escape_markdown(post_data['title'])
        escaped_content = escape_markdown(post_data['content'])

        message = f"🌵 *Nová Kaktus akce\\!*\n\n*{escaped_title}*\n\n{escaped_content}"

        successful_sends = 0

        for chat_id in active_users:
            # Use retry logic for network errors
            success = await self._send_message_with_retry(chat_id, message)

            if success:
                successful_sends += 1

            # Rate limiting between messages
            await asyncio.sleep(0.05)

        logger.info(f"Sent immediate notifications to {successful_sends}/{len(active_users)} users")
    
    async def schedule_reminder(self, post_data: Dict[str, Any]):
        """Schedule reminder message for event start time using JobQueue."""
        event_datetime = post_data.get('event_datetime')

        if not event_datetime:
            logger.info("No event datetime, skipping scheduled reminder")
            return

        if not is_valid_schedule_time(event_datetime):
            logger.warning(f"Event time {event_datetime} is not valid for scheduling")
            return

        # Calculate delay until event start time
        now = datetime.now(event_datetime.tzinfo)
        delay_seconds = (event_datetime - now).total_seconds()

        if delay_seconds <= 0:
            logger.warning(f"Event time {event_datetime} is in the past, skipping scheduled reminder")
            return

        logger.info(f"Scheduling reminder in {delay_seconds} seconds ({event_datetime})")

        # Schedule job using JobQueue
        if self.application.job_queue is None:
            logger.error("JobQueue not available. Install with: pip install 'python-telegram-bot[job-queue]'")
            return

        self.application.job_queue.run_once(
            callback=self._send_reminder_job,
            when=delay_seconds,
            data=post_data,
            name=f"reminder_{post_data.get('post_hash', 'unknown')}"
        )

    async def _send_reminder_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Job callback to send reminder message with retry logic for network errors."""
        post_data = context.job.data

        try:
            # Get active users at the time of sending (not when scheduled)
            active_users = self.db_manager.get_active_users()

            if not active_users:
                logger.info("No active users for scheduled reminder")
                return

            # Escape title to prevent Markdown parsing errors
            escaped_title = escape_markdown(post_data['title'])

            reminder_message = f"⏰ *Připomínka: Kaktus akce začíná nyní\\!*\n\n*{escaped_title}*"

            successful_sends = 0

            for chat_id in active_users:
                # Use retry logic for network errors
                success = await self._send_message_with_retry(
                    chat_id=chat_id,
                    message=reminder_message,
                    bot=context.bot
                )

                if success:
                    successful_sends += 1

                # Rate limiting between messages
                await asyncio.sleep(0.05)

            logger.info(f"Sent scheduled reminders to {successful_sends}/{len(active_users)} users for: {post_data['title']}")

        except Exception as e:
            logger.error(f"Error in reminder job: {e}")
    
    async def handle_new_post(self, post_data: Dict[str, Any]):
        """Handle new post by sending immediate notification and scheduling reminder."""
        logger.info(f"Handling new post: {post_data['title']}")

        await self.send_immediate_notification(post_data)

        # Mark notifications as sent after successful delivery
        self.db_manager.mark_notifications_sent(post_data['post_hash'])

        await self.schedule_reminder(post_data)
    
    async def start_bot(self):
        """Start the Telegram bot."""
        await self.application.initialize()
        await self.application.start()
        logger.info("Telegram bot started successfully")
    
    async def stop_bot(self):
        """Stop the Telegram bot."""
        await self.application.stop()
        await self.application.shutdown()
        logger.info("Telegram bot stopped")
    
    def run_polling(self):
        """Run bot in polling mode (for testing)."""
        self.application.run_polling()