import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
import requests

from src.scraper import KaktusScraper
from src.database import DatabaseManager

class TestKaktusScraper:
    
    @pytest.fixture
    def scraper(self, db_manager):
        """Create KaktusScraper instance for testing."""
        return KaktusScraper('https://test.example.com', db_manager, 60)
    
    def test_scraper_initialization(self, scraper, db_manager):
        """Test scraper initialization."""
        assert scraper.url == 'https://test.example.com'
        assert scraper.db_manager == db_manager
        assert scraper.check_interval == 60
        assert scraper.session is not None
        assert 'Mozilla' in scraper.session.headers['User-Agent']
    
    def test_fetch_page_success(self, scraper, mock_requests_get):
        """Test successful webpage fetching."""
        mock_response = Mock()
        mock_response.content = b'<html><body><h1>Test</h1></body></html>'
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        result = scraper.fetch_page()
        
        assert result is not None
        assert isinstance(result, BeautifulSoup)
        assert result.find('h1').text == 'Test'
        mock_requests_get.assert_called_once_with('https://test.example.com', timeout=30)
    
    def test_fetch_page_request_error(self, scraper, mock_requests_get):
        """Test webpage fetching with request error."""
        mock_requests_get.side_effect = requests.RequestException("Network error")
        
        result = scraper.fetch_page()
        
        assert result is None
    
    def test_fetch_page_timeout(self, scraper, mock_requests_get):
        """Test webpage fetching with timeout."""
        mock_requests_get.side_effect = requests.Timeout("Request timeout")
        
        result = scraper.fetch_page()
        
        assert result is None

class TestScraperExtractPost:
    
    @pytest.fixture
    def scraper(self, db_manager):
        return KaktusScraper('https://test.example.com', db_manager, 60)
    
    def test_extract_latest_post_article_tag(self, scraper, sample_html):
        """Test extracting post from article tag."""
        soup = BeautifulSoup(sample_html, 'html.parser')
        
        result = scraper.extract_latest_post(soup)
        
        assert result is not None
        assert result['title'] == 'Dobíječka 9.9.2025 15:00 - 18:00'
        assert 'Test content for Kaktus event' in result['content']
        assert result['event_datetime'] is not None
        assert result['post_hash'] is not None
    
    def test_extract_latest_post_div_with_post_class(self, scraper):
        """Test extracting post from div with post class."""
        html = '''
        <html>
            <body>
                <div class="post">
                    <h3>Event 15.10.2025 14:00 - 16:00</h3>
                    <p>Event description here</p>
                </div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        result = scraper.extract_latest_post(soup)
        
        assert result is not None
        assert result['title'] == 'Event 15.10.2025 14:00 - 16:00'
        assert 'Event description here' in result['content']
    
    def test_extract_latest_post_title_with_class(self, scraper):
        """Test extracting post with title class."""
        html = '''
        <html>
            <body>
                <article>
                    <div class="title">Special Event 20.11.2025 10:00 - 12:00</div>
                    <div class="content">Special event details</div>
                </article>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        result = scraper.extract_latest_post(soup)
        
        assert result is not None
        assert result['title'] == 'Special Event 20.11.2025 10:00 - 12:00'
        assert 'Special event details' in result['content']
    
    def test_extract_latest_post_no_articles(self, scraper):
        """Test extracting when no articles are found."""
        html = '<html><body><p>No articles here</p></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        result = scraper.extract_latest_post(soup)
        
        assert result is None
    
    def test_extract_latest_post_no_title(self, scraper):
        """Test extracting when no title is found."""
        html = '''
        <html>
            <body>
                <article>
                    <p>Content without title</p>
                </article>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        result = scraper.extract_latest_post(soup)
        
        assert result is None
    
    def test_extract_latest_post_multiple_articles(self, scraper):
        """Test extracting the first (latest) article when multiple exist."""
        html = '''
        <html>
            <body>
                <article>
                    <h2>Latest Event 25.12.2025 18:00 - 20:00</h2>
                    <p>Latest content</p>
                </article>
                <article>
                    <h2>Old Event 20.12.2025 15:00 - 17:00</h2>
                    <p>Old content</p>
                </article>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        result = scraper.extract_latest_post(soup)
        
        assert result is not None
        assert result['title'] == 'Latest Event 25.12.2025 18:00 - 20:00'
        assert 'Latest content' in result['content']
    
    def test_extract_latest_post_exception_handling(self, scraper):
        """Test exception handling in extract_latest_post."""
        with patch('src.scraper.parse_czech_datetime', side_effect=Exception("Parse error")):
            soup = BeautifulSoup('<article><h2>Test</h2></article>', 'html.parser')
            
            result = scraper.extract_latest_post(soup)
            
            assert result is None

class TestScraperCheckForNewPosts:
    
    @pytest.fixture
    def scraper(self, db_manager):
        return KaktusScraper('https://test.example.com', db_manager, 60)
    
    def test_check_for_new_posts_new_post(self, scraper, sample_html, mock_requests_get):
        """Test checking for new posts when new post is found."""
        mock_response = Mock()
        mock_response.content = sample_html.encode()
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        with patch.object(scraper.db_manager, 'is_post_processed', return_value=False), \
             patch.object(scraper.db_manager, 'add_processed_post', return_value=True):
            
            result = scraper.check_for_new_posts()
            
            assert result is not None
            assert result['title'] == 'Dobíječka 9.9.2025 15:00 - 18:00'
    
    def test_check_for_new_posts_already_processed(self, scraper, sample_html, mock_requests_get):
        """Test checking for posts when post is already processed."""
        mock_response = Mock()
        mock_response.content = sample_html.encode()
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        with patch.object(scraper.db_manager, 'is_post_processed', return_value=True):
            
            result = scraper.check_for_new_posts()
            
            assert result is None
    
    def test_check_for_new_posts_fetch_failure(self, scraper, mock_requests_get):
        """Test checking for posts when fetch fails."""
        mock_requests_get.side_effect = requests.RequestException("Network error")
        
        result = scraper.check_for_new_posts()
        
        assert result is None
    
    def test_check_for_new_posts_no_post_extracted(self, scraper, mock_requests_get):
        """Test checking when no post can be extracted."""
        mock_response = Mock()
        mock_response.content = b'<html><body><p>No articles</p></body></html>'
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        result = scraper.check_for_new_posts()
        
        assert result is None
    
    def test_check_for_new_posts_database_add_failure(self, scraper, sample_html, mock_requests_get):
        """Test checking when database add fails."""
        mock_response = Mock()
        mock_response.content = sample_html.encode()
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        
        with patch.object(scraper.db_manager, 'is_post_processed', return_value=False), \
             patch.object(scraper.db_manager, 'add_processed_post', return_value=False):
            
            result = scraper.check_for_new_posts()
            
            assert result is None

class TestScraperMonitoring:
    
    @pytest.fixture
    def scraper(self, db_manager):
        return KaktusScraper('https://test.example.com', db_manager, 1)
    
    @pytest.mark.asyncio
    async def test_start_monitoring_new_post_found(self, scraper, sample_post_data):
        """Test monitoring when new post is found."""
        callback = Mock()
        callback.return_value = None
        
        call_count = 0
        def mock_check_for_new_posts():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return sample_post_data
            return None
        
        with patch.object(scraper, 'check_for_new_posts', side_effect=mock_check_for_new_posts), \
             patch('asyncio.sleep') as mock_sleep:
            
            async def stop_after_two_iterations():
                await asyncio.sleep(0.1)
                mock_sleep.side_effect = asyncio.CancelledError()
            
            task = asyncio.create_task(scraper.start_monitoring(callback))
            stop_task = asyncio.create_task(stop_after_two_iterations())
            
            try:
                await asyncio.gather(task, stop_task)
            except asyncio.CancelledError:
                pass
            
            callback.assert_called_once_with(sample_post_data)
    
    @pytest.mark.asyncio
    async def test_start_monitoring_no_new_posts(self, scraper):
        """Test monitoring when no new posts are found."""
        callback = Mock()
        
        with patch.object(scraper, 'check_for_new_posts', return_value=None), \
             patch('asyncio.sleep') as mock_sleep:
            
            call_count = 0
            async def mock_sleep_side_effect(duration):
                nonlocal call_count
                call_count += 1
                if call_count >= 2:
                    raise asyncio.CancelledError()
            
            mock_sleep.side_effect = mock_sleep_side_effect
            
            try:
                await scraper.start_monitoring(callback)
            except asyncio.CancelledError:
                pass
            
            callback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_start_monitoring_exception_handling(self, scraper):
        """Test monitoring exception handling."""
        callback = Mock()
        
        with patch.object(scraper, 'check_for_new_posts', side_effect=Exception("Test error")), \
             patch('asyncio.sleep') as mock_sleep:
            
            call_count = 0
            async def mock_sleep_side_effect(duration):
                nonlocal call_count
                call_count += 1
                if call_count >= 2:
                    raise asyncio.CancelledError()
            
            mock_sleep.side_effect = mock_sleep_side_effect
            
            try:
                await scraper.start_monitoring(callback)
            except asyncio.CancelledError:
                pass
            
            assert call_count >= 2
    
    def test_scraper_cleanup(self, scraper):
        """Test scraper session cleanup."""
        session = scraper.session
        
        del scraper
        
        assert session.close

class TestScraperEdgeCases:
    
    @pytest.fixture
    def scraper(self, db_manager):
        return KaktusScraper('https://test.example.com', db_manager, 60)
    
    def test_extract_post_with_unicode_content(self, scraper):
        """Test extracting post with unicode characters."""
        html = '''
        <html>
            <body>
                <article>
                    <h2>Nabíjení 15.10.2025 14:00 - 16:00 🔋</h2>
                    <p>Speciální akce s českou diaktikou a emoji 📱</p>
                </article>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        result = scraper.extract_latest_post(soup)
        
        assert result is not None
        assert '🔋' in result['title']
        assert 'českou' in result['content']
        assert '📱' in result['content']
    
    def test_extract_post_with_nested_content(self, scraper):
        """Test extracting post with nested HTML content."""
        html = '''
        <html>
            <body>
                <article>
                    <h2>Event 20.11.2025 10:00 - 12:00</h2>
                    <div class="content">
                        <p>First paragraph</p>
                        <div>
                            <span>Nested content</span>
                        </div>
                        <p>Last paragraph</p>
                    </div>
                </article>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        result = scraper.extract_latest_post(soup)
        
        assert result is not None
        assert 'First paragraph' in result['content']
        assert 'Nested content' in result['content']
        assert 'Last paragraph' in result['content']