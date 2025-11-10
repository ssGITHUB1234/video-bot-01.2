#!/usr/bin/env python3
"""
Initialize database schema
Run this script to create all necessary tables
"""

import os
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with schema"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set")
        return False
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Read schema file
        logger.info("Reading schema file...")
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
        
        # Execute schema
        logger.info("Creating tables...")
        cur.execute(schema_sql)
        conn.commit()
        
        logger.info("Database initialized successfully!")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == '__main__':
    success = init_database()
    exit(0 if success else 1)
