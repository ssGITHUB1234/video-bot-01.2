#!/usr/bin/env python3
"""
Migration script to transfer data from JSON files to PostgreSQL database
Run this once after setting up PostgreSQL
"""

import json
import os
import logging
from storage import Storage

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def migrate_data():
    """Migrate all JSON data to PostgreSQL"""
    
    # Initialize storage (connects to PostgreSQL)
    storage = Storage()
    
    logger.info("Starting data migration from JSON to PostgreSQL...")
    
    # Define JSON file paths
    data_dir = 'data'
    json_files = {
        'users': os.path.join(data_dir, 'users.json'),
        'videos': os.path.join(data_dir, 'videos.json'),
        'ads': os.path.join(data_dir, 'ads.json'),
        'messages': os.path.join(data_dir, 'messages.json'),
        'user_states': os.path.join(data_dir, 'user_states.json')
    }
    
    # Track migration stats
    stats = {
        'users': 0,
        'videos': 0,
        'ads': 0,
        'messages': 0,
        'user_states': 0
    }
    
    # Migrate Users
    if os.path.exists(json_files['users']):
        logger.info("Migrating users...")
        with open(json_files['users'], 'r', encoding='utf-8') as f:
            users_data = json.load(f)
            for user_id, user_info in users_data.items():
                try:
                    storage.save_user(int(user_id), user_info)
                    stats['users'] += 1
                except Exception as e:
                    logger.error(f"Error migrating user {user_id}: {e}")
        logger.info(f"Migrated {stats['users']} users")
    
    # Migrate Videos
    if os.path.exists(json_files['videos']):
        logger.info("Migrating videos...")
        with open(json_files['videos'], 'r', encoding='utf-8') as f:
            videos_data = json.load(f)
            for video_id, video_info in videos_data.items():
                try:
                    storage.save_video(video_info)
                    stats['videos'] += 1
                except Exception as e:
                    logger.error(f"Error migrating video {video_id}: {e}")
        logger.info(f"Migrated {stats['videos']} videos")
    
    # Migrate Ads
    if os.path.exists(json_files['ads']):
        logger.info("Migrating ads...")
        with open(json_files['ads'], 'r', encoding='utf-8') as f:
            ads_data = json.load(f)
            for ad_id, ad_info in ads_data.items():
                try:
                    storage.save_ad(ad_info)
                    stats['ads'] += 1
                except Exception as e:
                    logger.error(f"Error migrating ad {ad_id}: {e}")
        logger.info(f"Migrated {stats['ads']} ads")
    
    # Migrate Messages
    if os.path.exists(json_files['messages']):
        logger.info("Migrating messages...")
        try:
            with open(json_files['messages'], 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content and content != '{}':
                    messages_data = json.loads(content)
                    for message_key, message_info in messages_data.items():
                        try:
                            storage.save_message_tracking(message_key, message_info)
                            stats['messages'] += 1
                        except Exception as e:
                            logger.error(f"Error migrating message {message_key}: {e}")
                else:
                    logger.info("Messages file is empty, skipping...")
        except Exception as e:
            logger.warning(f"Could not read messages file: {e}, skipping...")
        logger.info(f"Migrated {stats['messages']} messages")
    
    # Migrate User States
    if os.path.exists(json_files['user_states']):
        logger.info("Migrating user states...")
        try:
            with open(json_files['user_states'], 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content and content != '{}':
                    states_data = json.loads(content)
                    for user_id, state_info in states_data.items():
                        try:
                            storage.save_user_state(int(user_id), state_info)
                            stats['user_states'] += 1
                        except Exception as e:
                            logger.error(f"Error migrating user state {user_id}: {e}")
                else:
                    logger.info("User states file is empty, skipping...")
        except Exception as e:
            logger.warning(f"Could not read user states file: {e}, skipping...")
        logger.info(f"Migrated {stats['user_states']} user states")
    
    # Print final stats
    logger.info("\n" + "="*50)
    logger.info("MIGRATION COMPLETE!")
    logger.info("="*50)
    logger.info(f"✓ Users:       {stats['users']}")
    logger.info(f"✓ Videos:      {stats['videos']}")
    logger.info(f"✓ Ads:         {stats['ads']}")
    logger.info(f"✓ Messages:    {stats['messages']}")
    logger.info(f"✓ User States: {stats['user_states']}")
    logger.info("="*50)
    logger.info("\nYour data has been successfully migrated to PostgreSQL!")
    logger.info("You can now safely delete the 'data/' directory if desired.")
    logger.info("PostgreSQL will automatically persist all future data.")
    
    return stats

if __name__ == '__main__':
    try:
        migrate_data()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
