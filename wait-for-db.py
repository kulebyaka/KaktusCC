#!/usr/bin/env python3
"""
Database readiness check script.
Waits for PostgreSQL database to be ready before starting the application.
"""

import sys
import time
import psycopg2
from urllib.parse import urlparse
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_database_url(database_url):
    """Parse database URL into components."""
    parsed = urlparse(database_url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password
    }

def wait_for_db(database_url, max_retries=30, retry_delay=2):
    """Wait for database to be ready."""
    db_config = parse_database_url(database_url)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Checking database connection (attempt {attempt + 1}/{max_retries})")
            
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            
            with conn.cursor() as cursor:
                cursor.execute('SELECT 1')
            
            conn.close()
            logger.info("Database is ready!")
            return True
            
        except psycopg2.OperationalError as e:
            logger.warning(f"Database not ready: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            else:
                logger.error("Database failed to become ready within timeout")
                return False
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    return False

if __name__ == '__main__':
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    if wait_for_db(database_url):
        logger.info("Database check passed")
        sys.exit(0)
    else:
        logger.error("Database check failed")
        sys.exit(1)