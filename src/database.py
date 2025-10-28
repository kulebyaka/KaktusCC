from sqlalchemy import create_engine, Column, BigInteger, String, Text, Boolean, DateTime, Integer, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.sql import func
from sqlalchemy.exc import OperationalError
from datetime import datetime
from typing import List, Optional, Dict
import logging
import time

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    chat_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_started = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ProcessedPost(Base):
    __tablename__ = 'processed_posts'
    
    id = Column(Integer, primary_key=True)
    post_hash = Column(String(64), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    event_datetime = Column(DateTime(timezone=True))
    notifications_sent = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._connect_with_retry()
        
    def _connect_with_retry(self, max_retries: int = 5, retry_delay: int = 5):
        """Connect to database with retry logic."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting database connection (attempt {attempt + 1}/{max_retries})")
                self.engine = create_engine(self.database_url)
                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                
                # Test the connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                
                logger.info("Database connection successful")
                return
                
            except OperationalError as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("All database connection attempts failed")
                    raise
        
    def create_tables(self):
        """Create database tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def add_user(self, chat_id: int, username: str = None) -> bool:
        """Add or reactivate a user."""
        session = self.get_session()
        try:
            existing_user = session.query(User).filter(User.chat_id == chat_id).first()
            
            if existing_user:
                if not existing_user.is_active:
                    existing_user.is_active = True
                    session.commit()
                    logger.info(f"Reactivated user {chat_id}")
                    return True
                else:
                    logger.info(f"User {chat_id} already active")
                    return False
            else:
                new_user = User(chat_id=chat_id, username=username)
                session.add(new_user)
                session.commit()
                logger.info(f"Added new user {chat_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding user {chat_id}: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def deactivate_user(self, chat_id: int) -> bool:
        """Deactivate a user."""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.chat_id == chat_id).first()
            if user:
                user.is_active = False
                session.commit()
                logger.info(f"Deactivated user {chat_id}")
                return True
            else:
                logger.warning(f"User {chat_id} not found for deactivation")
                return False
                
        except Exception as e:
            logger.error(f"Error deactivating user {chat_id}: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_active_users(self) -> List[int]:
        """Get list of active user chat IDs."""
        session = self.get_session()
        try:
            users = session.query(User.chat_id).filter(User.is_active == True).all()
            return [user.chat_id for user in users]
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
        finally:
            session.close()
    
    def is_post_processed(self, post_hash: str) -> bool:
        """Check if post has been processed AND notifications have been sent."""
        session = self.get_session()
        try:
            post = session.query(ProcessedPost).filter(ProcessedPost.post_hash == post_hash).first()
            # Consider processed only if notifications were successfully sent
            return post is not None and post.notifications_sent
        except Exception as e:
            logger.error(f"Error checking processed post: {e}")
            return False
        finally:
            session.close()
    
    def add_processed_post(self, post_hash: str, title: str, content: str,
                          event_datetime: Optional[datetime] = None) -> bool:
        """Add a processed post to database with notifications_sent=False.
        Returns True if newly added, False if already exists."""
        session = self.get_session()
        try:
            # Check if post already exists
            existing = session.query(ProcessedPost).filter(ProcessedPost.post_hash == post_hash).first()
            if existing:
                logger.debug(f"Post already exists in database: {title}")
                return False

            post = ProcessedPost(
                post_hash=post_hash,
                title=title,
                content=content,
                event_datetime=event_datetime,
                notifications_sent=False
            )
            session.add(post)
            session.commit()
            logger.info(f"Added processed post: {title}")
            return True
        except Exception as e:
            logger.error(f"Error adding processed post: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def add_past_post(self, post_hash: str, title: str, content: str,
                      event_datetime: Optional[datetime] = None) -> bool:
        """Add a past event post to database with notifications_sent=True.
        This is used during deployment to skip sending notifications for old events.

        Returns True if newly added, False if already exists."""
        session = self.get_session()
        try:
            # Check if post already exists
            existing = session.query(ProcessedPost).filter(ProcessedPost.post_hash == post_hash).first()
            if existing:
                logger.debug(f"Past post already exists in database: {title}")
                return False

            post = ProcessedPost(
                post_hash=post_hash,
                title=title,
                content=content,
                event_datetime=event_datetime,
                notifications_sent=True  # Mark as sent to skip notifications
            )
            session.add(post)
            session.commit()
            logger.info(f"Added past post (notifications skipped): {title}")
            return True
        except Exception as e:
            logger.error(f"Error adding past post: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def mark_notifications_sent(self, post_hash: str) -> bool:
        """Mark notifications as sent for a processed post."""
        session = self.get_session()
        try:
            post = session.query(ProcessedPost).filter(ProcessedPost.post_hash == post_hash).first()
            if post:
                post.notifications_sent = True
                session.commit()
                logger.info(f"Marked notifications as sent for post: {post.title}")
                return True
            else:
                logger.warning(f"Post with hash {post_hash} not found")
                return False
        except Exception as e:
            logger.error(f"Error marking notifications as sent: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_unsent_posts(self) -> List[Dict]:
        """Get all posts that haven't had notifications sent yet."""
        session = self.get_session()
        try:
            posts = session.query(ProcessedPost).filter(ProcessedPost.notifications_sent == False).all()
            result = []
            for post in posts:
                result.append({
                    'post_hash': post.post_hash,
                    'title': post.title,
                    'content': post.content,
                    'event_datetime': post.event_datetime
                })
            return result
        except Exception as e:
            logger.error(f"Error getting unsent posts: {e}")
            return []
        finally:
            session.close()

    def mark_user_inactive_on_block(self, chat_id: int):
        """Mark user as inactive when bot is blocked."""
        self.deactivate_user(chat_id)