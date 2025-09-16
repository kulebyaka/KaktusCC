#!/bin/bash
set -e

echo "Starting Kaktus Telegram Bot..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
python wait-for-db.py

echo "Database is ready, starting application..."
python -m src.main