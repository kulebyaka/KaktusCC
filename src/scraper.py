import requests
from bs4 import BeautifulSoup
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import pytz
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
            # The site uses Next.js, so we need to extract from both rendered and embedded data

            # Strategy 1: Search for date patterns in the raw HTML (including JS payloads)
            # This handles Next.js server-side rendered data
            import re

            # Get the original HTML content as string to catch JS-embedded dates
            page_html = str(soup)

            # Search for Czech date patterns like "15. 10. 2025 15:00 - 17:00"
            # Note: The dot after day/month has a space in the format "15. 10."
            date_pattern = r'(\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s+\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})'
            matches = re.findall(date_pattern, page_html)

            if matches:
                logger.info(f"Found date patterns: {matches}")

                # Use the first date match as the event title
                event_date = matches[0].strip()
                # Normalize spacing in the date string
                event_date = re.sub(r'\s+', ' ', event_date)
                title = f"Dobíječka {event_date}"

                # Extract promotional content from main content area only (exclude nav/footer)
                content_parts = []

                # Strategy 1: Look for richTextStyles div (standard content area)
                rich_text_div = soup.find('div', class_='richTextStyles')

                if rich_text_div:
                    # Extract text from paragraphs only, excluding links to avoid "apce", "sámošce", etc.
                    for p in rich_text_div.find_all('p'):
                        # Get direct text content, excluding link text
                        for text in p.find_all(text=True, recursive=False):
                            cleaned = text.strip()
                            if cleaned and len(cleaned) > 10:
                                content_parts.append(cleaned)

                        # Also get text from strong tags within paragraphs
                        for strong in p.find_all('strong'):
                            cleaned = strong.get_text(strip=True)
                            if cleaned and len(cleaned) > 10 and cleaned not in content_parts:
                                content_parts.append(cleaned)

                # Strategy 2: If no richTextStyles, look for main content area
                if not content_parts:
                    main_section = soup.find('main')
                    if main_section:
                        # Get text from main, but exclude specific sections
                        # Remove navigation, forms, and footer before extracting text
                        for unwanted in main_section.find_all(['nav', 'form', 'footer']):
                            unwanted.decompose()

                        # Also remove divs with id="dobiti" or "dobit-kredit" (form section)
                        for unwanted in main_section.find_all(['div'], id=['dobiti', 'dobit-kredit']):
                            unwanted.decompose()

                        # Now extract meaningful content
                        for p in main_section.find_all('p'):
                            text = p.get_text(strip=True)
                            if text and len(text) > 20 and any(keyword in text.lower() for keyword in ['bonus', 'navíc', 'kč', 'akce']):
                                content_parts.append(text)

                content = ' '.join(content_parts[:3]) if content_parts else "Kaktus dobíjení akce"

                event_datetime = parse_czech_datetime(title)

                post_data = {
                    'title': title,
                    'content': content,
                    'event_datetime': event_datetime,
                    'post_hash': calculate_post_hash(title, event_datetime)
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
                            'post_hash': calculate_post_hash(title, event_datetime)
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
                        'post_hash': calculate_post_hash(title, None)
                    }

                    logger.info(f"Extracted general content: {title}")
                    return post_data
            
            logger.warning("No recognizable content found on Kaktus webpage")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting post: {e}")
            logger.debug(f"HTML sample: {str(soup)[:500]}...")
            return None
    
    def check_for_new_posts(self) -> Optional[Dict[str, Any]]:
        """Check for new posts and return post if notifications haven't been sent yet."""
        soup = self.fetch_page()
        if not soup:
            return None

        post_data = self.extract_latest_post(soup)
        if not post_data:
            return None

        # Check if post is fully processed (notifications sent)
        if self.db_manager.is_post_processed(post_data['post_hash']):
            logger.debug("Post already processed with notifications sent, skipping")
            return None

        # Check if event is in the past
        event_datetime = post_data.get('event_datetime')
        is_past_event = False

        if event_datetime:
            now = datetime.now(pytz.UTC)
            # Convert event_datetime to UTC for comparison
            if event_datetime.tzinfo is None:
                event_datetime_utc = pytz.UTC.localize(event_datetime)
            else:
                event_datetime_utc = event_datetime.astimezone(pytz.UTC)

            is_past_event = event_datetime_utc < now

        # Use different database methods based on whether event is in the past
        if is_past_event:
            # Add past event with notifications_sent=True to skip sending
            added = self.db_manager.add_past_post(
                post_data['post_hash'],
                post_data['title'],
                post_data['content'],
                post_data['event_datetime']
            )

            if added:
                logger.info(f"Past event detected and skipped: {post_data['title']}")

            # Don't send notifications for past events
            return None
        else:
            # Add regular post with notifications_sent=False
            added = self.db_manager.add_processed_post(
                post_data['post_hash'],
                post_data['title'],
                post_data['content'],
                post_data['event_datetime']
            )

            if added:
                logger.info(f"New post detected: {post_data['title']}")
            else:
                logger.info(f"Post exists but notifications not sent, retrying: {post_data['title']}")

            # Return post_data for notification sending
            return post_data
    
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