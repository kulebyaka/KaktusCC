from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import Forbidden, BadRequest
import logging
from typing import Dict, Any
from datetime import datetime
import asyncio
from .database import DatabaseManager
from .utils import datetime_to_unix_timestamp, is_valid_schedule_time

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
        """Send immediate notification to all active users."""
        active_users = self.db_manager.get_active_users()
        
        if not active_users:
            logger.info("No active users to notify")
            return
        
        message = f"🌵 **Nová Kaktus akce!**\n\n**{post_data['title']}**\n\n{post_data['content']}"
        
        successful_sends = 0
        
        for chat_id in active_users:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                successful_sends += 1
                
                await asyncio.sleep(0.05)
                
            except Forbidden:
                logger.warning(f"Bot blocked by user {chat_id}, marking as inactive")
                self.db_manager.mark_user_inactive_on_block(chat_id)
                
            except BadRequest as e:
                logger.error(f"Bad request when sending to {chat_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error sending notification to {chat_id}: {e}")
        
        logger.info(f"Sent immediate notifications to {successful_sends}/{len(active_users)} users")
    
    async def schedule_reminder(self, post_data: Dict[str, Any]):
        """Schedule reminder message for event start time."""
        event_datetime = post_data.get('event_datetime')
        
        if not event_datetime:
            logger.info("No event datetime, skipping scheduled reminder")
            return
        
        if not is_valid_schedule_time(event_datetime):
            logger.warning(f"Event time {event_datetime} is not valid for scheduling")
            return
        
        active_users = self.db_manager.get_active_users()
        
        if not active_users:
            logger.info("No active users for scheduled reminder")
            return
        
        schedule_timestamp = datetime_to_unix_timestamp(event_datetime)
        reminder_message = f"⏰ **Připomínka: Kaktus akce začíná nyní!**\n\n**{post_data['title']}**"
        
        successful_schedules = 0
        
        for chat_id in active_users:
            try:
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=reminder_message,
                    parse_mode='Markdown',
                    schedule_date=schedule_timestamp
                )
                successful_schedules += 1
                
                await asyncio.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Error scheduling reminder for {chat_id}: {e}")
        
        logger.info(f"Scheduled reminders for {successful_schedules}/{len(active_users)} users at {event_datetime}")
    
    async def handle_new_post(self, post_data: Dict[str, Any]):
        """Handle new post by sending immediate notification and scheduling reminder."""
        logger.info(f"Handling new post: {post_data['title']}")
        
        await self.send_immediate_notification(post_data)
        
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