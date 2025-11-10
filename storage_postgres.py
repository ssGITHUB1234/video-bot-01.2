"""
PostgreSQL-based storage system for bot data
"""

import psycopg2
import psycopg2.extras
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PostgreSQLStorage:
    def __init__(self, database_url: str):
        self.database_url = database_url
        
        # Test connection
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    # Video storage methods
    def save_video(self, video_data: Dict[str, Any]):
        """Save video data"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO videos (id, file_id, file_unique_id, duration, width, height, 
                                      file_size, thumbnail_file_id, message_id, channel_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        file_id = EXCLUDED.file_id,
                        file_unique_id = EXCLUDED.file_unique_id,
                        duration = EXCLUDED.duration,
                        width = EXCLUDED.width,
                        height = EXCLUDED.height,
                        file_size = EXCLUDED.file_size,
                        thumbnail_file_id = EXCLUDED.thumbnail_file_id,
                        message_id = EXCLUDED.message_id,
                        channel_id = EXCLUDED.channel_id
                """, (
                    video_data.get('id'),
                    video_data.get('file_id'),
                    video_data.get('file_unique_id'),
                    video_data.get('duration'),
                    video_data.get('width'),
                    video_data.get('height'),
                    video_data.get('file_size'),
                    video_data.get('thumbnail_file_id'),
                    video_data.get('message_id'),
                    video_data.get('channel_id')
                ))

    def get_video(self, video_id: str) -> Dict[str, Any]:
        """Get video data by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM videos WHERE id = %s", (video_id,))
                result = cur.fetchone()
                if result:
                    return dict(result)
                return {}

    def get_videos(self) -> Dict[str, Any]:
        """Get all videos"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM videos ORDER BY created_at DESC")
                rows = cur.fetchall()
                return {row['id']: dict(row) for row in rows}

    def delete_video(self, video_id: str):
        """Delete video by ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM videos WHERE id = %s", (video_id,))

    # Ad storage methods
    def save_ad(self, ad_data: Dict[str, Any]):
        """Save ad data"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ads (id, type, content, url, duration, active, views, last_shown, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET
                        type = EXCLUDED.type,
                        content = EXCLUDED.content,
                        url = EXCLUDED.url,
                        duration = EXCLUDED.duration,
                        active = EXCLUDED.active,
                        views = EXCLUDED.views,
                        last_shown = EXCLUDED.last_shown,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    ad_data.get('id'),
                    ad_data.get('type', 'text'),
                    ad_data.get('content'),
                    ad_data.get('url'),
                    ad_data.get('duration', 15),
                    ad_data.get('active', True),
                    ad_data.get('views', 0),
                    ad_data.get('last_shown')
                ))

    def get_ad(self, ad_id: str) -> Dict[str, Any]:
        """Get ad data by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM ads WHERE id = %s", (ad_id,))
                result = cur.fetchone()
                if result:
                    ad = dict(result)
                    # Convert timestamps to ISO format
                    if ad.get('created_at'):
                        ad['created_at'] = ad['created_at'].isoformat()
                    if ad.get('updated_at'):
                        ad['updated_at'] = ad['updated_at'].isoformat()
                    if ad.get('last_shown'):
                        ad['last_shown'] = ad['last_shown'].isoformat()
                    return ad
                return {}

    def get_ads(self) -> Dict[str, Any]:
        """Get all ads"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM ads ORDER BY created_at DESC")
                rows = cur.fetchall()
                ads = {}
                for row in rows:
                    ad = dict(row)
                    # Convert timestamps to ISO format
                    if ad.get('created_at'):
                        ad['created_at'] = ad['created_at'].isoformat()
                    if ad.get('updated_at'):
                        ad['updated_at'] = ad['updated_at'].isoformat()
                    if ad.get('last_shown'):
                        ad['last_shown'] = ad['last_shown'].isoformat()
                    ads[ad['id']] = ad
                return ads

    def delete_ad(self, ad_id: str):
        """Delete ad by ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ads WHERE id = %s", (ad_id,))

    # Message tracking methods
    def save_message_tracking(self, message_key: str, message_data: Dict[str, Any]):
        """Save message tracking data"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO messages (message_key, user_id, chat_id, message_id, delete_at, is_video)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_key) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        chat_id = EXCLUDED.chat_id,
                        message_id = EXCLUDED.message_id,
                        delete_at = EXCLUDED.delete_at,
                        is_video = EXCLUDED.is_video
                """, (
                    message_key,
                    message_data.get('user_id'),
                    message_data.get('chat_id'),
                    message_data.get('message_id'),
                    message_data.get('delete_at'),
                    message_data.get('is_video', False)
                ))

    def get_message_tracking(self, message_key: str) -> Dict[str, Any]:
        """Get message tracking data by key"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM messages WHERE message_key = %s", (message_key,))
                result = cur.fetchone()
                return dict(result) if result else {}

    def get_all_message_tracking(self) -> Dict[str, Any]:
        """Get all message tracking data"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM messages")
                rows = cur.fetchall()
                return {row['message_key']: dict(row) for row in rows}

    def get_user_messages(self, user_id: int) -> Dict[str, Any]:
        """Get all messages for a specific user"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM messages WHERE user_id = %s", (user_id,))
                rows = cur.fetchall()
                return {row['message_key']: dict(row) for row in rows}

    def delete_message_tracking(self, message_key: str):
        """Delete message tracking data"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM messages WHERE message_key = %s", (message_key,))

    # User state methods
    def save_user_state(self, user_id: int, state_data: Dict[str, Any]):
        """Save user state data"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_states (user_id, ad_session_token, ad_session_start, 
                                            ad_id, video_id, ad_completed, ad_completed_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        ad_session_token = EXCLUDED.ad_session_token,
                        ad_session_start = EXCLUDED.ad_session_start,
                        ad_id = EXCLUDED.ad_id,
                        video_id = EXCLUDED.video_id,
                        ad_completed = EXCLUDED.ad_completed,
                        ad_completed_at = EXCLUDED.ad_completed_at,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    user_id,
                    state_data.get('ad_session_token'),
                    state_data.get('ad_session_start'),
                    state_data.get('ad_id'),
                    state_data.get('video_id'),
                    state_data.get('ad_completed', False),
                    state_data.get('ad_completed_at')
                ))

    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        """Get user state by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM user_states WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
                if result:
                    state = dict(result)
                    # Convert timestamps to ISO format
                    if state.get('ad_session_start'):
                        state['ad_session_start'] = state['ad_session_start'].isoformat()
                    if state.get('ad_completed_at'):
                        state['ad_completed_at'] = state['ad_completed_at'].isoformat()
                    if state.get('updated_at'):
                        state['updated_at'] = state['updated_at'].isoformat()
                    return state
                return {}

    def get_user_states(self) -> Dict[str, Any]:
        """Get all user states"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM user_states")
                rows = cur.fetchall()
                return {str(row['user_id']): dict(row) for row in rows}
    
    def save_user_states(self, user_states: Dict[str, Any]):
        """Save multiple user states (for compatibility)"""
        for user_id, state_data in user_states.items():
            self.save_user_state(int(user_id), state_data)

    def delete_user_state(self, user_id: int):
        """Delete user state"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_states WHERE user_id = %s", (user_id,))

    # Ad completion tracking methods
    def start_ad_session(self, user_id: int, ad_id: str, video_id: str, session_token: str):
        """Start an ad viewing session with a unique token"""
        state_data = {
            'ad_session_token': session_token,
            'ad_session_start': datetime.now().isoformat(),
            'ad_id': ad_id,
            'video_id': video_id,
            'ad_completed': False
        }
        self.save_user_state(user_id, state_data)
        logger.info(f"Ad session started for user {user_id} with token {session_token}")

    def mark_ad_completed(self, user_id: int, ad_id: str, video_id: str, session_token: str) -> bool:
        """Mark an ad as completed by a user if session is valid"""
        user_state = self.get_user_state(user_id)
        
        if not user_state:
            logger.warning(f"No session found for user {user_id}")
            return False
        
        # Validate session token
        if user_state.get('ad_session_token') != session_token:
            logger.warning(f"Invalid session token for user {user_id}")
            return False
        
        # Validate video_id matches
        if user_state.get('video_id') != video_id:
            logger.warning(f"Video ID mismatch for user {user_id}")
            return False
        
        # Mark as completed
        state_data = {
            **user_state,
            'ad_completed': True,
            'ad_completed_at': datetime.now().isoformat()
        }
        self.save_user_state(user_id, state_data)
        logger.info(f"Ad {ad_id} marked as completed for user {user_id}")
        return True

    def check_ad_completed(self, user_id: int, video_id: str) -> bool:
        """Check if user has completed ad for a specific video"""
        user_state = self.get_user_state(user_id)
        return (user_state.get('ad_completed') == True and 
                user_state.get('video_id') == video_id)

    def clear_ad_completion(self, user_id: int):
        """Clear ad completion status for a user"""
        state_data = {
            'ad_completed': False,
            'ad_id': None,
            'video_id': None
        }
        self.save_user_state(user_id, state_data)
        logger.info(f"Ad completion cleared for user {user_id}")

    # User tracking methods
    def save_user(self, user_id: int, user_data: Dict[str, Any]):
        """Save or update user data"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Check if user exists
                cur.execute("SELECT interaction_count FROM users WHERE user_id = %s", (user_id,))
                existing = cur.fetchone()
                
                if existing:
                    # Update existing user
                    cur.execute("""
                        UPDATE users SET
                            username = COALESCE(%s, username),
                            first_name = COALESCE(%s, first_name),
                            last_interaction = CURRENT_TIMESTAMP,
                            interaction_count = interaction_count + 1
                        WHERE user_id = %s
                    """, (
                        user_data.get('username'),
                        user_data.get('first_name'),
                        user_id
                    ))
                else:
                    # Insert new user
                    cur.execute("""
                        INSERT INTO users (user_id, username, first_name, first_interaction, 
                                         last_interaction, interaction_count)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                    """, (
                        user_id,
                        user_data.get('username', ''),
                        user_data.get('first_name', '')
                    ))
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user data by ID"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
                if result:
                    user = dict(result)
                    # Convert timestamps to ISO format
                    if user.get('first_interaction'):
                        user['first_interaction'] = user['first_interaction'].isoformat()
                    if user.get('last_interaction'):
                        user['last_interaction'] = user['last_interaction'].isoformat()
                    return user
                return {}
    
    def get_all_users(self) -> Dict[str, Any]:
        """Get all users"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM users ORDER BY first_interaction DESC")
                rows = cur.fetchall()
                users = {}
                for row in rows:
                    user = dict(row)
                    # Convert timestamps to ISO format
                    if user.get('first_interaction'):
                        user['first_interaction'] = user['first_interaction'].isoformat()
                    if user.get('last_interaction'):
                        user['last_interaction'] = user['last_interaction'].isoformat()
                    users[str(user['user_id'])] = user
                return users
    
    def get_user_count(self) -> int:
        """Get total number of users"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                return cur.fetchone()[0]

    # Utility methods (for compatibility with old JSON-based code)
    def backup_data(self) -> str:
        """Create a backup notification (actual DB backups handled by Render)"""
        logger.info("Using PostgreSQL - backups are automatically managed by Render")
        return "Render PostgreSQL automatic backups active"

    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore notification (use Render dashboard for DB restores)"""
        logger.warning("Database restore should be done through Render dashboard")
        return False

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                stats = {}
                
                # Count records in each table
                for table in ['users', 'videos', 'ads', 'messages', 'user_states', 'admin_sessions']:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cur.fetchone()[0]
                
                stats['storage_type'] = 'PostgreSQL'
                stats['database_url'] = 'Connected'
                
                return stats

    # Admin session methods
    def create_admin_session(self, token: str, created_at: float, last_activity: float):
        """Create a new admin session (used on login only)"""
        from datetime import datetime
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                created_dt = datetime.fromtimestamp(created_at)
                activity_dt = datetime.fromtimestamp(last_activity)
                cur.execute("""
                    INSERT INTO admin_sessions (token, created_at, last_activity)
                    VALUES (%s, %s, %s)
                """, (token, created_dt, activity_dt))

    def update_admin_session_activity(self, token: str, last_activity: float) -> bool:
        """Update session activity timestamp if session exists (returns True if updated)"""
        from datetime import datetime
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                activity_dt = datetime.fromtimestamp(last_activity)
                cur.execute("""
                    UPDATE admin_sessions 
                    SET last_activity = %s 
                    WHERE token = %s
                """, (activity_dt, token))
                return cur.rowcount > 0

    def get_all_admin_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all admin sessions"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM admin_sessions")
                rows = cur.fetchall()
                sessions = {}
                for row in rows:
                    sessions[row['token']] = {
                        'created_at': row['created_at'].timestamp() if row.get('created_at') else 0,
                        'last_activity': row['last_activity'].timestamp() if row.get('last_activity') else 0
                    }
                return sessions

    def delete_admin_session(self, token: str):
        """Delete a specific admin session"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM admin_sessions WHERE token = %s", (token,))
