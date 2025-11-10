"""
Storage system for bot data - automatically selects PostgreSQL or JSON storage
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def Storage():
    """
    Storage facade that returns the appropriate storage backend
    based on environment configuration.
    
    Returns PostgreSQL storage when DATABASE_URL is available and valid.
    Falls back to JSON storage for development/testing.
    """
    database_url = os.getenv('DATABASE_URL', '').strip()
    
    # Use PostgreSQL if DATABASE_URL is set and not empty
    if database_url:
        try:
            from storage_postgres import PostgreSQLStorage
            logger.info("Using PostgreSQL storage (production mode)")
            
            # Initialize database if needed
            _initialize_database_if_needed(database_url)
            
            return PostgreSQLStorage(database_url)
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {e}")
            logger.info("Falling back to JSON storage")
            from storage_json import JSONStorage
            return JSONStorage()
    else:
        # Use JSON storage for development
        logger.info("DATABASE_URL not set - using JSON storage (development mode)")
        from storage_json import JSONStorage
        return JSONStorage()

def _initialize_database_if_needed(database_url: str):
    """Initialize database schema if tables don't exist"""
    import psycopg2
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Check if tables exist
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        tables_exist = cur.fetchone()[0]
        
        if not tables_exist:
            logger.info("Database tables not found, initializing schema...")
            
            # Read and execute schema
            with open('schema.sql', 'r') as f:
                schema_sql = f.read()
            
            cur.execute(schema_sql)
            conn.commit()
            logger.info("Database schema initialized successfully!")
        else:
            logger.info("Database tables already exist")
            
            # Check if is_video column exists in messages table
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'messages' AND column_name = 'is_video'
                );
            """)
            column_exists = cur.fetchone()[0]
            
            if not column_exists:
                logger.info("Adding is_video column to messages table...")
                cur.execute("ALTER TABLE messages ADD COLUMN is_video BOOLEAN DEFAULT FALSE;")
                conn.commit()
                logger.info("Database schema updated successfully!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error checking/initializing database: {e}")
        raise
