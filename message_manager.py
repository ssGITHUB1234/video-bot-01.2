"""
Message manager for handling 24-hour auto-deletion and user message tracking
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from telegram import Bot
from telegram.ext import ContextTypes
from storage import Storage

logger = logging.getLogger(__name__)

class MessageManager:
    def __init__(self, storage: Storage):
        self.storage = storage
        self.cleanup_running = False
        self.bot = None

    async def track_and_schedule_deletion(self, context: Optional[ContextTypes.DEFAULT_TYPE], 
                                        user_id: int, message_id: int, 
                                        delete_previous: bool = True, bot: Optional[Bot] = None,
                                        is_video: bool = False):
        """
        Track message for deletion and optionally delete previous messages
        
        Args:
            context: Telegram context (can be None if bot is provided)
            user_id: User ID
            message_id: Message ID to track
            delete_previous: Whether to delete previous messages from this user
            bot: Bot instance (used when context is None)
            is_video: Whether this message is a video (videos are kept for 24h)
        """
        try:
            bot_instance = bot or context.bot
            
            # Delete previous messages for this user if requested
            if delete_previous:
                await self._delete_user_previous_messages(bot_instance, user_id)
            
            # Track new message
            message_data = {
                'user_id': user_id,
                'chat_id': user_id,  # For DMs, chat_id = user_id
                'message_id': message_id,
                'created_at': datetime.now().isoformat(),
                'delete_at': (datetime.now() + timedelta(hours=24)).isoformat(),
                'deleted': False,
                'is_video': is_video
            }
            
            self.storage.save_message_tracking(f"{user_id}_{message_id}", message_data)
            
            logger.debug(f"Message {message_id} tracked for user {user_id} (is_video={is_video})")
            
        except Exception as e:
            logger.error(f"Error tracking message {message_id} for user {user_id}: {e}")

    async def _delete_user_previous_messages(self, bot: Bot, user_id: int):
        """
        Delete all previous NON-VIDEO messages for a user immediately.
        Video messages are kept for 24 hours before deletion.
        """
        try:
            messages = self.storage.get_user_messages(user_id)
            
            for msg_key, msg_data in messages.items():
                if not msg_data.get('deleted', False):
                    # If it's a video message, don't delete it now (will be deleted after 24h)
                    if msg_data.get('is_video', False):
                        logger.debug(f"Keeping video message {msg_data['message_id']} for 24h deletion")
                        continue
                    
                    # Delete non-video messages immediately
                    try:
                        await bot.delete_message(
                            chat_id=user_id, 
                            message_id=msg_data['message_id']
                        )
                        
                        # Mark as deleted
                        msg_data['deleted'] = True
                        msg_data['deleted_at'] = datetime.now().isoformat()
                        self.storage.save_message_tracking(msg_key, msg_data)
                        
                        logger.debug(f"Deleted previous non-video message {msg_data['message_id']} for user {user_id}")
                        
                    except Exception as e:
                        # Message might be already deleted or too old
                        logger.debug(f"Could not delete message {msg_data['message_id']}: {e}")
                        # Mark as deleted anyway to avoid future attempts
                        msg_data['deleted'] = True
                        msg_data['deleted_at'] = datetime.now().isoformat()
                        self.storage.save_message_tracking(msg_key, msg_data)
                        
        except Exception as e:
            logger.error(f"Error deleting previous messages for user {user_id}: {e}")

    def set_bot(self, bot: Bot):
        """Set the bot instance for message deletion"""
        self.bot = bot
        logger.info("Bot instance set for MessageManager")

    async def start_cleanup_scheduler(self):
        """Start the background task for message cleanup"""
        if self.cleanup_running:
            return
        
        self.cleanup_running = True
        logger.info("Message cleanup scheduler started")
        
        try:
            while self.cleanup_running:
                await self._cleanup_expired_messages()
                # Check every hour
                await asyncio.sleep(3600)
                
        except Exception as e:
            logger.error(f"Cleanup scheduler error: {e}")
            self.cleanup_running = False

    async def _cleanup_expired_messages(self):
        """Clean up expired messages (24+ hours old)"""
        try:
            if not self.bot:
                logger.warning("Bot instance not set, cannot delete messages")
                return
            
            messages = self.storage.get_all_message_tracking()
            
            if not messages:
                logger.debug("No messages to clean up")
                return
            
            now = datetime.now()
            deleted_count = 0
            
            for msg_key, msg_data in messages.items():
                if not msg_data or not isinstance(msg_data, dict):
                    logger.warning(f"Invalid message data for key {msg_key}, skipping")
                    continue
                    
                if msg_data.get('deleted', False):
                    continue
                
                delete_at = msg_data.get('delete_at')
                if not delete_at:
                    logger.warning(f"Message {msg_key} missing delete_at field, skipping")
                    continue
                
                try:
                    if isinstance(delete_at, datetime):
                        delete_time = delete_at
                    elif isinstance(delete_at, str):
                        delete_time = datetime.fromisoformat(delete_at)
                    else:
                        logger.warning(f"Invalid delete_at type for message {msg_key}: {type(delete_at)}")
                        continue
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing delete_at for message {msg_key}: {e}")
                    continue
                
                if now >= delete_time:
                    try:
                        user_id = msg_data.get('user_id')
                        message_id = msg_data.get('message_id')
                        
                        if not user_id or not message_id:
                            logger.warning(f"Message {msg_key} missing user_id or message_id")
                            continue
                        
                        await self.bot.delete_message(
                            chat_id=user_id,
                            message_id=message_id
                        )
                        
                        msg_data['deleted'] = True
                        msg_data['deleted_at'] = now.isoformat()
                        self.storage.save_message_tracking(msg_key, msg_data)
                        
                        deleted_count += 1
                        logger.info(f"Deleted expired message {message_id} for user {user_id}")
                        
                    except Exception as e:
                        logger.debug(f"Could not delete message {msg_data.get('message_id')}: {e}")
                        msg_data['deleted'] = True
                        msg_data['deleted_at'] = now.isoformat()
                        self.storage.save_message_tracking(msg_key, msg_data)
            
            if deleted_count > 0:
                logger.info(f"Successfully deleted {deleted_count} expired messages")
                
        except Exception as e:
            logger.error(f"Error in cleanup process: {e}", exc_info=True)

    def get_user_message_count(self, user_id: int) -> int:
        """Get count of tracked messages for a user"""
        messages = self.storage.get_user_messages(user_id)
        active_messages = sum(1 for msg in messages.values() 
                            if not msg.get('deleted', False) and not msg.get('expired', False))
        return active_messages

    def get_message_statistics(self) -> dict:
        """Get message tracking statistics"""
        all_messages = self.storage.get_all_message_tracking()
        
        if not all_messages:
            return {
                'total_messages': 0,
                'active_messages': 0,
                'deleted_messages': 0,
                'expired_messages': 0,
                'unique_users': 0
            }
        
        total_messages = len(all_messages)
        deleted_messages = sum(1 for msg in all_messages.values() if msg and isinstance(msg, dict) and msg.get('deleted', False))
        expired_messages = sum(1 for msg in all_messages.values() if msg and isinstance(msg, dict) and msg.get('expired', False))
        active_messages = total_messages - deleted_messages - expired_messages
        
        unique_users = len(set(msg.get('user_id') for msg in all_messages.values() if msg and isinstance(msg, dict) and msg.get('user_id')))
        
        return {
            'total_messages': total_messages,
            'active_messages': active_messages,
            'deleted_messages': deleted_messages,
            'expired_messages': expired_messages,
            'unique_users': unique_users
        }

    def cleanup_old_tracking_data(self, days_old: int = 7):
        """Clean up tracking data older than specified days"""
        try:
            messages = self.storage.get_all_message_tracking()
            cutoff_date = datetime.now() - timedelta(days=days_old)
            removed_count = 0
            
            for msg_key, msg_data in list(messages.items()):
                if not msg_data or not isinstance(msg_data, dict):
                    continue
                
                created_at_raw = msg_data.get('created_at')
                if not created_at_raw:
                    continue
                
                if isinstance(created_at_raw, datetime):
                    created_at = created_at_raw
                elif isinstance(created_at_raw, str):
                    created_at = datetime.fromisoformat(created_at_raw)
                else:
                    continue
                
                if created_at < cutoff_date and (msg_data.get('deleted', False) or msg_data.get('expired', False)):
                    self.storage.delete_message_tracking(msg_key)
                    removed_count += 1
            
            logger.info(f"Cleaned up {removed_count} old tracking records")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old tracking data: {e}")
            return 0

    def stop_cleanup_scheduler(self):
        """Stop the cleanup scheduler"""
        self.cleanup_running = False
        logger.info("Message cleanup scheduler stopped")
