import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from .utils import calculate_post_hash, parse_czech_datetime
from .database import DatabaseManager

logger = logging.getLogger(__name__)

class KaktusScraper:
    def __init__(self, url: str, db_manager: DatabaseManager, check_interval: int = 300):
        self.url = url
        self.db_manager = db_manager
        self.check_interval = check_interval
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def fetch_page(self) -> Optional[BeautifulSoup]:
        """Fetch and parse the webpage."""
        try:
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            logger.info("Successfully fetched webpage")
            return soup
            
        except requests.RequestException as e:
            logger.error(f"Error fetching webpage: {e}")
            return None
    
    def extract_latest_post(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract the latest post from the Kaktus webpage."""
        try:
            # First, let's add debug logging to see what we're working with
            logger.debug(f"HTML title: {soup.title.string if soup.title else 'No title'}")
            logger.debug(f"Page has {len(soup.find_all())} total elements")
            
            # Look for the specific Kaktus promotional content
            # The site appears to have promotional events with dates
            
            # Strategy 1: Look for date patterns in the entire page text
            page_text = soup.get_text()
            date_matches = []
            
            # Search for Czech date patterns like "9.9.2025 15:00 - 18:00"
            import re
            date_pattern = r'(\d{1,2}\.\d{1,2}\.\d{4}\s+\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})'
            matches = re.findall(date_pattern, page_text)
            
            if matches:
                logger.info(f"Found date patterns: {matches}")
                
                # Use the first date match as the event title
                event_date = matches[0]
                title = f"Dobíječka {event_date}"
                
                # Look for promotional content around the date
                content_parts = []
                
                # Look for bonus information
                if "bonus" in page_text.lower() or "navíc" in page_text.lower():
                    # Extract promotional details
                    lines = page_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if any(keyword in line.lower() for keyword in ['bonus', 'navíc', 'dobij', 'kredit', 'kč']):
                            if len(line) > 10 and len(line) < 200:  # Reasonable length
                                content_parts.append(line)
                
                content = ' '.join(content_parts[:3]) if content_parts else "Kaktus dobíjení akce"
                
                event_datetime = parse_czech_datetime(title)
                
                post_data = {
                    'title': title,
                    'content': content,
                    'event_datetime': event_datetime,
                    'post_hash': calculate_post_hash(title, content)
                }
                
                logger.info(f"Extracted Kaktus event: {title}")
                return post_data
            
            # Strategy 2: Look for specific promotional content sections
            # Check for elements containing promotional text
            promo_indicators = ['dobíječka', 'akce', 'bonus', 'navíc', 'kredit']
            
            for indicator in promo_indicators:
                elements = soup.find_all(text=lambda text: text and indicator.lower() in text.lower())
                if elements:
                    logger.info(f"Found promotional content with '{indicator}'")
                    
                    # Try to construct a meaningful post from the promotional content
                    promo_text = ' '.join([elem.strip() for elem in elements if len(elem.strip()) > 5])[:500]
                    
                    # Look for any date pattern in the promotional text
                    event_datetime = None
                    for text in elements:
                        parsed_date = parse_czech_datetime(str(text))
                        if parsed_date:
                            event_datetime = parsed_date
                            break
                    
                    if promo_text:
                        title = "Kaktus akce" + (f" {event_datetime.strftime('%d.%m.%Y')}" if event_datetime else "")
                        
                        post_data = {
                            'title': title,
                            'content': promo_text,
                            'event_datetime': event_datetime,
                            'post_hash': calculate_post_hash(title, promo_text)
                        }
                        
                        logger.info(f"Extracted promotional content: {title}")
                        return post_data
            
            # Strategy 3: Look for any meaningful content with structured elements
            main_content = soup.find('main') or soup.find('body')
            if main_content:
                # Get all text content and look for substantial paragraphs
                paragraphs = main_content.find_all(['p', 'div', 'span'], string=True)
                meaningful_content = []
                
                for p in paragraphs:
                    text = p.get_text(strip=True) if hasattr(p, 'get_text') else str(p).strip()
                    if len(text) > 20 and any(keyword in text.lower() for keyword in ['kaktus', 'dobíj', 'kredit', 'akce']):
                        meaningful_content.append(text)
                
                if meaningful_content:
                    title = "Kaktus - aktuální nabídka"
                    content = ' '.join(meaningful_content[:3])
                    
                    post_data = {
                        'title': title,
                        'content': content,
                        'event_datetime': None,
                        'post_hash': calculate_post_hash(title, content)
                    }
                    
                    logger.info(f"Extracted general content: {title}")
                    return post_data
            
            logger.warning("No recognizable content found on Kaktus webpage")
            logger.debug(f"Page text sample: {page_text[:200]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting post: {e}")
            logger.debug(f"HTML sample: {str(soup)[:500]}...")
            return None
    
    def check_for_new_posts(self) -> Optional[Dict[str, Any]]:
        """Check for new posts and return new post if found."""
        soup = self.fetch_page()
        if not soup:
            return None
        
        post_data = self.extract_latest_post(soup)
        if not post_data:
            return None
        
        if self.db_manager.is_post_processed(post_data['post_hash']):
            logger.info("Post already processed, skipping")
            return None
        
        if self.db_manager.add_processed_post(
            post_data['post_hash'],
            post_data['title'],
            post_data['content'],
            post_data['event_datetime']
        ):
            logger.info(f"New post detected: {post_data['title']}")
            return post_data
        
        return None
    
    async def start_monitoring(self, callback):
        """Start monitoring for new posts."""
        logger.info(f"Starting webpage monitoring every {self.check_interval} seconds")
        
        while True:
            try:
                new_post = self.check_for_new_posts()
                if new_post:
                    await callback(new_post)
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    def __del__(self):
        """Clean up session on deletion."""
        if hasattr(self, 'session'):
            self.session.close()