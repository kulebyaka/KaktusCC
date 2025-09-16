#!/usr/bin/env python3
"""
Debug script to test the scraper independently.
Usage: python debug-scraper.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scraper import KaktusScraper
from database import DatabaseManager
from config import Config
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def main():
    print("🔍 Kaktus Scraper Debug Tool")
    print("=" * 50)
    
    # Load configuration
    Config.setup_logging()
    
    # Create a mock database manager (won't actually save to DB)
    class MockDatabaseManager:
        def is_post_processed(self, post_hash):
            return False
        
        def add_processed_post(self, post_hash, title, content, event_datetime=None):
            print(f"✅ Would save post: {title}")
            return True
    
    mock_db = MockDatabaseManager()
    
    # Create scraper
    scraper = KaktusScraper(Config.SCRAPE_URL, mock_db, 60)
    
    print(f"📡 Fetching: {Config.SCRAPE_URL}")
    print("-" * 50)
    
    # Fetch and parse the page
    soup = scraper.fetch_page()
    if not soup:
        print("❌ Failed to fetch webpage")
        return
    
    print("✅ Page fetched successfully")
    print(f"📄 Page title: {soup.title.string if soup.title else 'No title'}")
    print(f"📊 Total elements: {len(soup.find_all())}")
    
    print("\n" + "=" * 50)
    print("🔍 Extracting post content...")
    print("-" * 50)
    
    # Extract post
    post_data = scraper.extract_latest_post(soup)
    
    if post_data:
        print("✅ Post extracted successfully!")
        print(f"📝 Title: {post_data['title']}")
        print(f"📅 Event datetime: {post_data['event_datetime']}")
        print(f"📄 Content: {post_data['content'][:200]}...")
        print(f"🔒 Hash: {post_data['post_hash'][:16]}...")
    else:
        print("❌ No post data extracted")
        
        # Show some debug info
        page_text = soup.get_text()
        print(f"\n📝 Page text sample (first 300 chars):")
        print("-" * 30)
        print(page_text[:300])
        print("-" * 30)
        
        # Look for specific keywords
        keywords = ['dobíječka', 'akce', 'bonus', 'navíc', 'kredit', 'kaktus']
        print(f"\n🔍 Keyword analysis:")
        for keyword in keywords:
            count = page_text.lower().count(keyword.lower())
            print(f"  {keyword}: {count} occurrences")
    
    print("\n" + "=" * 50)
    print("✅ Debug complete!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Debug script failed: {e}")
        import traceback
        traceback.print_exc()