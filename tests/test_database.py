import pytest
from datetime import datetime
import pytz
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import IntegrityError

from src.database import DatabaseManager, User, ProcessedPost

class TestDatabaseManager:
    
    def test_create_tables(self, db_manager):
        """Test that create_tables() creates database tables."""
        db_manager.create_tables()
        
        session = db_manager.get_session()
        try:
            result = session.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in result.fetchall()]
            
            assert 'users' in tables
            assert 'processed_posts' in tables
        finally:
            session.close()
    
    def test_get_session(self, db_manager):
        """Test that get_session() returns a valid session."""
        session = db_manager.get_session()
        
        assert session is not None
        session.close()

class TestDatabaseManagerUsers:
    
    def test_add_user_new_user(self, db_manager):
        """Test adding a new user."""
        db_manager.create_tables()
        
        result = db_manager.add_user(12345, 'testuser')
        
        assert result is True
        
        session = db_manager.get_session()
        try:
            user = session.query(User).filter(User.chat_id == 12345).first()
            assert user is not None
            assert user.username == 'testuser'
            assert user.is_active is True
        finally:
            session.close()
    
    def test_add_user_existing_active_user(self, db_manager):
        """Test adding an already active user."""
        db_manager.create_tables()
        
        db_manager.add_user(12345, 'testuser')
        result = db_manager.add_user(12345, 'testuser')
        
        assert result is False
    
    def test_add_user_reactivate_inactive_user(self, db_manager):
        """Test reactivating an inactive user."""
        db_manager.create_tables()
        
        db_manager.add_user(12345, 'testuser')
        db_manager.deactivate_user(12345)
        
        result = db_manager.add_user(12345, 'testuser')
        
        assert result is True
        
        session = db_manager.get_session()
        try:
            user = session.query(User).filter(User.chat_id == 12345).first()
            assert user.is_active is True
        finally:
            session.close()
    
    def test_add_user_without_username(self, db_manager):
        """Test adding user without username."""
        db_manager.create_tables()
        
        result = db_manager.add_user(12345)
        
        assert result is True
        
        session = db_manager.get_session()
        try:
            user = session.query(User).filter(User.chat_id == 12345).first()
            assert user.username is None
        finally:
            session.close()
    
    def test_add_user_database_error(self, db_manager):
        """Test handling database error when adding user."""
        db_manager.create_tables()
        
        with patch.object(db_manager, 'get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.query.side_effect = Exception("Database error")
            mock_get_session.return_value = mock_session
            
            result = db_manager.add_user(12345, 'testuser')
            
            assert result is False
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_deactivate_user_existing_user(self, db_manager):
        """Test deactivating an existing user."""
        db_manager.create_tables()
        
        db_manager.add_user(12345, 'testuser')
        result = db_manager.deactivate_user(12345)
        
        assert result is True
        
        session = db_manager.get_session()
        try:
            user = session.query(User).filter(User.chat_id == 12345).first()
            assert user.is_active is False
        finally:
            session.close()
    
    def test_deactivate_user_nonexistent_user(self, db_manager):
        """Test deactivating a non-existent user."""
        db_manager.create_tables()
        
        result = db_manager.deactivate_user(99999)
        
        assert result is False
    
    def test_get_active_users(self, db_manager):
        """Test getting list of active users."""
        db_manager.create_tables()
        
        db_manager.add_user(12345, 'user1')
        db_manager.add_user(67890, 'user2')
        db_manager.add_user(11111, 'user3')
        db_manager.deactivate_user(67890)
        
        active_users = db_manager.get_active_users()
        
        assert len(active_users) == 2
        assert 12345 in active_users
        assert 11111 in active_users
        assert 67890 not in active_users
    
    def test_get_active_users_empty(self, db_manager):
        """Test getting active users when none exist."""
        db_manager.create_tables()
        
        active_users = db_manager.get_active_users()
        
        assert active_users == []
    
    def test_mark_user_inactive_on_block(self, db_manager):
        """Test marking user inactive when blocked."""
        db_manager.create_tables()
        
        db_manager.add_user(12345, 'testuser')
        
        with patch.object(db_manager, 'deactivate_user') as mock_deactivate:
            db_manager.mark_user_inactive_on_block(12345)
            mock_deactivate.assert_called_once_with(12345)

class TestDatabaseManagerPosts:
    
    def test_is_post_processed_new_post(self, db_manager):
        """Test checking if a new post is processed."""
        db_manager.create_tables()
        
        result = db_manager.is_post_processed('new_hash_123')
        
        assert result is False
    
    def test_is_post_processed_existing_post(self, db_manager):
        """Test checking if an existing post is processed."""
        db_manager.create_tables()
        
        db_manager.add_processed_post('existing_hash', 'Test Title', 'Test Content')
        
        result = db_manager.is_post_processed('existing_hash')
        
        assert result is True
    
    def test_add_processed_post_success(self, db_manager):
        """Test successfully adding a processed post."""
        db_manager.create_tables()
        
        prague_tz = pytz.timezone('Europe/Prague')
        event_time = prague_tz.localize(datetime(2025, 9, 9, 15, 0))
        
        result = db_manager.add_processed_post(
            'test_hash',
            'Test Title',
            'Test Content',
            event_time
        )
        
        assert result is True
        
        session = db_manager.get_session()
        try:
            post = session.query(ProcessedPost).filter(
                ProcessedPost.post_hash == 'test_hash'
            ).first()
            
            assert post is not None
            assert post.title == 'Test Title'
            assert post.content == 'Test Content'
            assert post.event_datetime == event_time
            assert post.notifications_sent is True
        finally:
            session.close()
    
    def test_add_processed_post_without_datetime(self, db_manager):
        """Test adding processed post without event datetime."""
        db_manager.create_tables()
        
        result = db_manager.add_processed_post(
            'test_hash',
            'Test Title',
            'Test Content'
        )
        
        assert result is True
        
        session = db_manager.get_session()
        try:
            post = session.query(ProcessedPost).filter(
                ProcessedPost.post_hash == 'test_hash'
            ).first()
            
            assert post.event_datetime is None
        finally:
            session.close()
    
    def test_add_processed_post_duplicate_hash(self, db_manager):
        """Test adding processed post with duplicate hash."""
        db_manager.create_tables()
        
        db_manager.add_processed_post('duplicate_hash', 'Title 1', 'Content 1')
        result = db_manager.add_processed_post('duplicate_hash', 'Title 2', 'Content 2')
        
        assert result is False
    
    def test_add_processed_post_database_error(self, db_manager):
        """Test handling database error when adding processed post."""
        db_manager.create_tables()
        
        with patch.object(db_manager, 'get_session') as mock_get_session:
            mock_session = MagicMock()
            mock_session.add.side_effect = Exception("Database error")
            mock_get_session.return_value = mock_session
            
            result = db_manager.add_processed_post('hash', 'title', 'content')
            
            assert result is False
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

class TestDatabaseModels:
    
    def test_user_model_creation(self, db_manager):
        """Test User model creation and defaults."""
        db_manager.create_tables()
        
        session = db_manager.get_session()
        try:
            user = User(chat_id=12345, username='testuser')
            session.add(user)
            session.commit()
            
            retrieved_user = session.query(User).filter(User.chat_id == 12345).first()
            
            assert retrieved_user.chat_id == 12345
            assert retrieved_user.username == 'testuser'
            assert retrieved_user.is_active is True
            assert retrieved_user.first_started is not None
            assert retrieved_user.created_at is not None
        finally:
            session.close()
    
    def test_processed_post_model_creation(self, db_manager):
        """Test ProcessedPost model creation and defaults."""
        db_manager.create_tables()
        
        session = db_manager.get_session()
        try:
            post = ProcessedPost(
                post_hash='test_hash',
                title='Test Title',
                content='Test Content'
            )
            session.add(post)
            session.commit()
            
            retrieved_post = session.query(ProcessedPost).filter(
                ProcessedPost.post_hash == 'test_hash'
            ).first()
            
            assert retrieved_post.post_hash == 'test_hash'
            assert retrieved_post.title == 'Test Title'
            assert retrieved_post.content == 'Test Content'
            assert retrieved_post.notifications_sent is False
            assert retrieved_post.processed_at is not None
        finally:
            session.close()