"""
Main bot handler for Telegram video sharing bot
Handles all Telegram interactions and coordinates other components
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatType
from video_processor import VideoProcessor
from ad_manager import AdManager
from message_manager import MessageManager
from storage import Storage

logger = logging.getLogger(__name__)

class TelegramBotHandler:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.private_channel_id = os.getenv('PRIVATE_CHANNEL_ID')
        self.public_channel_id = os.getenv('PUBLIC_CHANNEL_ID')
        self.owner_id = os.getenv('OWNER_ID')
        
        if not all([self.bot_token, self.private_channel_id, self.public_channel_id]):
            raise ValueError("Missing required environment variables: BOT_TOKEN, PRIVATE_CHANNEL_ID, PUBLIC_CHANNEL_ID")
        
        # Convert channel IDs to integers (handle invite links)
        self.private_channel_id = self._extract_channel_id(self.private_channel_id)
        self.public_channel_id = self._extract_channel_id(self.public_channel_id)
        
        # Convert owner ID to integer
        try:
            self.owner_id = int(self.owner_id) if self.owner_id else None
        except (ValueError, TypeError):
            logger.warning("OWNER_ID not set or invalid. Owner-only commands will be disabled.")
            self.owner_id = None
        
        # Initialize components
        self.storage = Storage()
        self.video_processor = VideoProcessor(self.storage)
        self.ad_manager = AdManager(self.storage)
        self.message_manager = MessageManager(self.storage)
        
        # Debug: Print channel IDs
        logger.info(f"Private Channel ID: {self.private_channel_id}")
        logger.info(f"Public Channel ID: {self.public_channel_id}")
        if self.owner_id:
            logger.info(f"Owner ID: {self.owner_id}")
        
        # Initialize bot application
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")
        # Disable updater for webhook mode
        self.application = Application.builder().token(self.bot_token).updater(None).build()
        self._setup_handlers()

    def _extract_channel_id(self, channel_input):
        """Extract numeric channel ID from various input formats"""
        if not channel_input:
            raise ValueError("Channel ID cannot be empty")
        
        # If it's already a number or starts with -, it's likely a channel ID
        if str(channel_input).lstrip('-').isdigit():
            return int(channel_input)
        
        # For invite links, we need to get the actual channel ID using the bot
        # For now, we'll use a placeholder approach - the user needs to provide numeric IDs
        if 'https://t.me/' in str(channel_input) or '@' in str(channel_input):
            raise ValueError(f"Please provide the numeric channel ID instead of invite link/username: {channel_input}")
        
        try:
            return int(channel_input)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid channel ID format: {channel_input}. Please provide a numeric channel ID (e.g., -1001234567890)")

    def _setup_handlers(self):
        """Setup all bot handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        
        # Channel post handlers (for videos posted to channels)
        if self.private_channel_id:
            logger.info(f"Setting up channel post video handler for private channel: {self.private_channel_id}")
            self.application.add_handler(MessageHandler(
                filters.UpdateType.CHANNEL_POST & filters.VIDEO & filters.Chat(chat_id=int(self.private_channel_id)),
                self.handle_channel_post_video
            ))
            # Also handle videos sent as documents (some clients send videos this way)
            logger.info(f"Setting up channel post document handler for private channel: {self.private_channel_id}")
            self.application.add_handler(MessageHandler(
                filters.UpdateType.CHANNEL_POST & filters.Document.VIDEO & filters.Chat(chat_id=int(self.private_channel_id)),
                self.handle_channel_post_document_video
            ))
        
        # Message handlers (for regular user messages - excludes channel posts)
        if self.private_channel_id:
            logger.info(f"Setting up regular video handler for private channel: {self.private_channel_id}")
            self.application.add_handler(MessageHandler(
                filters.UpdateType.MESSAGE & filters.VIDEO & filters.Chat(chat_id=int(self.private_channel_id)), 
                self.handle_private_channel_video
            ))
        
        # Callback query handler for button clicks
        self.application.add_handler(CallbackQueryHandler(self.handle_button_click))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    def _is_owner(self, user_id: int) -> bool:
        """Check if user is the bot owner"""
        return self.owner_id is not None and user_id == self.owner_id
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        
        self.storage.save_user(user_id, {
            'username': update.effective_user.username,
            'first_name': update.effective_user.first_name
        })
        
        welcome_msg = (
            "🔞 Welcome to the YPV Bot!\n\n"
            "Click 'Watch Now' buttons on videos in our public channel to receive videos in your DM.\n"
            "Our channel:- https://t.me/+az0ZkCs4Ay42YTE1\n\n"
            "Each video is preceded by a short ad.\n\n"
            "Enjoy watching! 🍿"
        )
        
        # Send welcome message and schedule deletion
        message = await update.message.reply_text(welcome_msg)
        await self.message_manager.track_and_schedule_deletion(
            context, user_id, message.message_id, delete_previous=True
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        help_msg = (
            "🆘 Bot Help\n\n"
            "• Click 'Watch Now' buttons to receive videos\n"
            "• Watch a 5-second ad before each video\n"
            "• Videos are sent directly to your DM\n"
            "• Messages auto-delete after 24 hours\n"
            "• Only one message per user at a time\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
        )
        
        message = await update.message.reply_text(help_msg)
        await self.message_manager.track_and_schedule_deletion(
            context, user_id, message.message_id, delete_previous=True
        )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show bot statistics (owner only)"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        
        if not self._is_owner(user_id):
            message = await update.message.reply_text("❌ This command is only available to the bot owner.")
            await self.message_manager.track_and_schedule_deletion(
                context, user_id, message.message_id, delete_previous=True
            )
            return
        
        videos = self.storage.get_videos()
        ads = self.storage.get_ads()
        all_users = self.storage.get_all_users()
        user_states = self.storage.get_user_states()
        
        active_users_24h = 0
        for user_data in all_users.values():
            last_interaction = user_data.get('last_interaction')
            if last_interaction:
                try:
                    last_time = datetime.fromisoformat(last_interaction)
                    if datetime.now() - last_time < timedelta(hours=24):
                        active_users_24h += 1
                except:
                    pass
        
        stats_msg = (
            "📊 Bot Statistics\n\n"
            f"👥 Total Users: {len(all_users)}\n"
            f"🟢 Active (24h): {active_users_24h}\n"
            f"🎬 Total Videos: {len(videos)}\n"
            f"📢 Total Ads: {len(ads)}\n"
            f"⏳ Pending States: {len(user_states)}\n\n"
            f"🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        message = await update.message.reply_text(stats_msg)
        await self.message_manager.track_and_schedule_deletion(
            context, user_id, message.message_id, delete_previous=True
        )
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command - send message to all users (owner only)"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        
        if not self._is_owner(user_id):
            message = await update.message.reply_text("❌ This command is only available to the bot owner.")
            await self.message_manager.track_and_schedule_deletion(
                context, user_id, message.message_id, delete_previous=True
            )
            return
        
        if not context.args:
            message = await update.message.reply_text(
                "📢 Broadcast Command\n\n"
                "Usage: /broadcast <message>\n\n"
                "Example: /broadcast Hello everyone! New update available!\n\n"
                "This will send your message to all bot users."
            )
            await self.message_manager.track_and_schedule_deletion(
                context, user_id, message.message_id, delete_previous=True
            )
            return
        
        broadcast_message = ' '.join(context.args)
        all_users = self.storage.get_all_users()
        
        if not all_users:
            message = await update.message.reply_text("❌ No users found to broadcast to.")
            await self.message_manager.track_and_schedule_deletion(
                context, user_id, message.message_id, delete_previous=True
            )
            return
        
        status_msg = await update.message.reply_text(
            f"📤 Starting broadcast to {len(all_users)} users...\n\n"
            "⏳ Please wait..."
        )
        
        success_count = 0
        failed_count = 0
        blocked_count = 0
        
        for user_key, user_data in all_users.items():
            try:
                target_user_id = user_data.get('user_id')
                if not target_user_id:
                    try:
                        target_user_id = int(user_key)
                    except (ValueError, TypeError):
                        logger.warning(f"Skipping invalid user_id: {user_key}")
                        failed_count += 1
                        continue
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"📢 Broadcast Message\n\n{broadcast_message}"
                )
                success_count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                error_msg = str(e).lower()
                if "blocked" in error_msg or "forbidden" in error_msg:
                    blocked_count += 1
                    logger.info(f"User {user_key} has blocked the bot")
                else:
                    failed_count += 1
                    logger.warning(f"Failed to send broadcast to user {user_key}: {e}")
        
        result_msg = (
            f"✅ Broadcast Complete!\n\n"
            f"📊 Results:\n"
            f"✅ Sent: {success_count}\n"
            f"🚫 Blocked: {blocked_count}\n"
            f"❌ Failed: {failed_count}\n"
            f"📈 Total: {len(all_users)}"
        )
        
        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_msg.message_id,
            text=result_msg
        )

    async def handle_private_channel_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video uploads in private channel"""
        try:
            if not update.message:
                return
            video = update.message.video
            if not video:
                return
            
            logger.info(f"New video uploaded: {video.file_id}")
            
            # Process the video and get caption/thumbnail
            video_data = await self.video_processor.process_video(
                context.bot, video, update.message
            )
            
            if not video_data:
                logger.error("Failed to process video")
                return
            
            # Create inline keyboard with Watch Now button that directly opens ad WebApp
            import os
            # Get domain for WebApp URL
            webhook_url = os.environ.get('WEBHOOK_URL')
            if webhook_url:
                base_url = webhook_url.rstrip('/')
            else:
                domains = os.environ.get('REPLIT_DOMAINS', 'localhost:5000')
                domain = domains.split(',')[0].strip() if ',' in domains else domains
                protocol = 'https://' if 'replit.dev' in domain else 'http://'
                base_url = f"{protocol}{domain}"
            
            # Create WebApp URL for direct ad access (user_id will be from callback)
            from telegram import WebAppInfo
            webapp_url = f"{base_url}/ad-redirect?video_id={video_data['id']}"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Watch Now", web_app=WebAppInfo(url=webapp_url))]
            ])
            
            # Get original caption (preserve exact formatting)
            original_caption = video_data.get('caption', '')
            
            # Reconstruct caption entities for formatting preservation
            from telegram import MessageEntity
            caption_entities = []
            if video_data.get('caption_entities'):
                for entity_data in video_data['caption_entities']:
                    entity = MessageEntity(
                        type=entity_data['type'],
                        offset=entity_data['offset'],
                        length=entity_data['length'],
                        url=entity_data.get('url')
                    )
                    caption_entities.append(entity)
            
            # Send ONLY thumbnail to public channel with "Watch Now" button
            # Users must click button, watch ads, and get full video in DM
            if self.public_channel_id:
                if video_data.get('thumbnail_bytes'):
                    # Send thumbnail as photo (downloaded bytes)
                    try:
                        from io import BytesIO
                        thumbnail_io = BytesIO(video_data['thumbnail_bytes'])
                        thumbnail_io.name = 'thumbnail.jpg'
                        
                        await context.bot.send_photo(
                            chat_id=int(self.public_channel_id),
                            photo=thumbnail_io,
                            caption=original_caption,
                            caption_entities=caption_entities if caption_entities else None,
                            reply_markup=keyboard
                        )
                        logger.info(f"Thumbnail image sent to public channel (full video hidden): {video_data['id']}")
                    except Exception as e:
                        logger.error(f"Failed to send thumbnail to public channel: {e}")
                        # Fallback: send a text post with watch button
                        try:
                            await context.bot.send_message(
                                chat_id=int(self.public_channel_id),
                                text=f"🎬 New Video\n\n{original_caption}\n\n👇 Click below to watch",
                                reply_markup=keyboard
                            )
                            logger.info(f"Text post sent to public channel (no thumbnail): {video_data['id']}")
                        except Exception as fallback_error:
                            logger.error(f"Failed to send fallback message: {fallback_error}")
                else:
                    # No thumbnail - send text message only
                    try:
                        await context.bot.send_message(
                            chat_id=int(self.public_channel_id),
                            text=f"🎬 New Video\n\n{original_caption}\n\n👇 Click below to watch",
                            reply_markup=keyboard
                        )
                        logger.info(f"Text post sent to public channel (no thumbnail available): {video_data['id']}")
                    except Exception as e:
                        logger.error(f"Failed to send message to public channel: {e}")
            
            logger.info(f"Video posted to public channel: {video_data['id']}")
            
        except Exception as e:
            logger.error(f"Error handling private channel video: {e}")

    async def handle_channel_post_document_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video documents in private channel (some apps send videos as documents)"""
        try:
            if not update.channel_post or not update.channel_post.document:
                return
            
            document = update.channel_post.document
            logger.info(f"New channel post document (video) uploaded: {document.file_id}, mime: {document.mime_type}")
            
            # Treat document as video for processing
            video_data = {
                'id': document.file_unique_id,
                'file_id': document.file_id,
                'file_unique_id': document.file_unique_id,
                'thumbnail_file_id': document.thumbnail.file_id if document.thumbnail else None,
                'file_size': document.file_size,
                'mime_type': document.mime_type,
                'file_name': document.file_name or f"video_{document.file_unique_id}",
                'uploaded_at': datetime.now().isoformat(),
                'message_id': update.channel_post.message_id,
                'caption': update.channel_post.caption or '',
                'caption_entities': [
                    {
                        'type': entity.type,
                        'offset': entity.offset,
                        'length': entity.length,
                        'url': entity.url if hasattr(entity, 'url') else None
                    } for entity in (update.channel_post.caption_entities or [])
                ]
            }
            
            # Save to storage
            self.storage.save_video(video_data)
            
            # Create inline keyboard
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Watch Now", callback_data=f"watch_{video_data['id']}")]
            ])
            
            # Get original caption
            original_caption = video_data.get('caption', '')
            
            # Reconstruct caption entities
            from telegram import MessageEntity
            caption_entities = []
            if video_data.get('caption_entities'):
                for entity_data in video_data['caption_entities']:
                    entity = MessageEntity(
                        type=entity_data['type'],
                        offset=entity_data['offset'],
                        length=entity_data['length'],
                        url=entity_data.get('url')
                    )
                    caption_entities.append(entity)
            
            # Send ONLY thumbnail to public channel, not the full document
            if self.public_channel_id:
                if video_data.get('thumbnail_file_id'):
                    # Try to send thumbnail (for documents, thumbnail might work directly)
                    try:
                        from io import BytesIO
                        # For documents, try getting thumbnail file
                        thumbnail_file = await context.bot.get_file(video_data['thumbnail_file_id'])
                        thumbnail_bytes = await thumbnail_file.download_as_bytearray()
                        thumbnail_io = BytesIO(thumbnail_bytes)
                        thumbnail_io.name = 'thumbnail.jpg'
                        
                        await context.bot.send_photo(
                            chat_id=int(self.public_channel_id),
                            photo=thumbnail_io,
                            caption=original_caption,
                            caption_entities=caption_entities if caption_entities else None,
                            reply_markup=keyboard
                        )
                        logger.info(f"Thumbnail sent to public channel (document video): {video_data['id']}")
                    except Exception as e:
                        logger.error(f"Failed to send thumbnail: {e}")
                        # Fallback to text
                        try:
                            await context.bot.send_message(
                                chat_id=int(self.public_channel_id),
                                text=f"🎬 New Video\n\n{original_caption}\n\n👇 Click below to watch",
                                reply_markup=keyboard
                            )
                        except:
                            pass
                else:
                    # No thumbnail - text only
                    try:
                        await context.bot.send_message(
                            chat_id=int(self.public_channel_id),
                            text=f"🎬 New Video\n\n{original_caption}\n\n👇 Click below to watch",
                            reply_markup=keyboard
                        )
                    except Exception as e:
                        logger.error(f"Failed to send message: {e}")
            
            logger.info(f"Document video posted to public channel: {video_data['id']}")
            
        except Exception as e:
            logger.error(f"Error handling channel post document video: {e}")

    async def handle_channel_post_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video posts in private channel (channel_post type)"""
        try:
            if not update.channel_post:
                return
            video = update.channel_post.video
            if not video:
                return
            
            logger.info(f"New channel post video uploaded: {video.file_id}")
            
            # Process the video and get caption/thumbnail
            video_data = await self.video_processor.process_video(
                context.bot, video, update.channel_post
            )
            
            if not video_data:
                logger.error("Failed to process channel post video")
                return
            
            # Create inline keyboard with Watch Now button that directly opens ad WebApp
            import os
            # Get domain for WebApp URL
            webhook_url = os.environ.get('WEBHOOK_URL')
            if webhook_url:
                base_url = webhook_url.rstrip('/')
            else:
                domains = os.environ.get('REPLIT_DOMAINS', 'localhost:5000')
                domain = domains.split(',')[0].strip() if ',' in domains else domains
                protocol = 'https://' if 'replit.dev' in domain else 'http://'
                base_url = f"{protocol}{domain}"
            
            # Create WebApp URL for direct ad access
            from telegram import WebAppInfo
            webapp_url = f"{base_url}/ad-redirect?video_id={video_data['id']}"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Watch Now", web_app=WebAppInfo(url=webapp_url))]
            ])
            
            # Get original caption (preserve exact formatting)
            original_caption = video_data.get('caption', '')
            
            # Reconstruct caption entities for formatting preservation
            from telegram import MessageEntity
            caption_entities = []
            if video_data.get('caption_entities'):
                for entity_data in video_data['caption_entities']:
                    entity = MessageEntity(
                        type=entity_data['type'],
                        offset=entity_data['offset'],
                        length=entity_data['length'],
                        url=entity_data.get('url')
                    )
                    caption_entities.append(entity)
            
            # Send ONLY thumbnail to public channel with "Watch Now" button
            # Users must click button, watch ads, and get full video in DM
            if self.public_channel_id:
                if video_data.get('thumbnail_bytes'):
                    # Send thumbnail as photo (downloaded bytes)
                    try:
                        from io import BytesIO
                        thumbnail_io = BytesIO(video_data['thumbnail_bytes'])
                        thumbnail_io.name = 'thumbnail.jpg'
                        
                        await context.bot.send_photo(
                            chat_id=int(self.public_channel_id),
                            photo=thumbnail_io,
                            caption=original_caption,
                            caption_entities=caption_entities if caption_entities else None,
                            reply_markup=keyboard
                        )
                        logger.info(f"Thumbnail image sent to public channel (full video hidden): {video_data['id']}")
                    except Exception as e:
                        logger.error(f"Failed to send thumbnail to public channel: {e}")
                        # Fallback: send a text post with watch button
                        try:
                            await context.bot.send_message(
                                chat_id=int(self.public_channel_id),
                                text=f"🎬 New Video\n\n{original_caption}\n\n👇 Click below to watch",
                                reply_markup=keyboard
                            )
                            logger.info(f"Text post sent to public channel (no thumbnail): {video_data['id']}")
                        except Exception as fallback_error:
                            logger.error(f"Failed to send fallback message: {fallback_error}")
                else:
                    # No thumbnail - send text message only
                    try:
                        await context.bot.send_message(
                            chat_id=int(self.public_channel_id),
                            text=f"🎬 New Video\n\n{original_caption}\n\n👇 Click below to watch",
                            reply_markup=keyboard
                        )
                        logger.info(f"Text post sent to public channel (no thumbnail available): {video_data['id']}")
                    except Exception as e:
                        logger.error(f"Failed to send message to public channel: {e}")
            
            logger.info(f"Channel post video posted to public channel: {video_data['id']}")
            
        except Exception as e:
            logger.error(f"Error handling channel post video: {e}")

    async def debug_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Debug handler to log all incoming messages"""
        try:
            logger.info(f"[DEBUG] ===== NEW UPDATE RECEIVED =====")
            logger.info(f"[DEBUG] Update type: {type(update)}")
            
            # Check for regular messages
            if update.message:
                chat_id = update.message.chat.id
                chat_type = update.message.chat.type
                message_type = "unknown"
                
                if update.message.video:
                    message_type = "video"
                    logger.info(f"[DEBUG] 🎬 VIDEO DETECTED! File ID: {update.message.video.file_id}")
                elif update.message.text:
                    message_type = "text"
                    logger.info(f"[DEBUG] 💬 TEXT: {update.message.text[:50]}...")
                elif update.message.photo:
                    message_type = "photo"
                elif update.message.document:
                    message_type = "document"
                
                logger.info(f"[DEBUG] 📍 MESSAGE - Chat ID: {chat_id} | Type: {chat_type} | Content: {message_type}")
                logger.info(f"[DEBUG] 🔑 Expected private channel: {self.private_channel_id}")
                if self.private_channel_id:
                    logger.info(f"[DEBUG] 🎯 Match private channel? {chat_id == int(self.private_channel_id)}")
                
                # Check if it's a video from the private channel specifically
                if update.message.video and chat_id == int(self.private_channel_id):
                    logger.info(f"[DEBUG] ✅ VIDEO FROM PRIVATE CHANNEL - SHOULD PROCESS!")
                elif update.message.video:
                    logger.info(f"[DEBUG] ❌ Video from wrong chat: {chat_id} (expected: {self.private_channel_id})")
                    
                # Log channel info if available
                if update.message.chat.title:
                    logger.info(f"[DEBUG] 📋 Channel title: {update.message.chat.title}")
                if update.message.from_user:
                    logger.info(f"[DEBUG] 👤 From user: {update.message.from_user.username} (ID: {update.message.from_user.id})")
                else:
                    logger.info(f"[DEBUG] 📢 Channel message (no from_user)")
            
            # Check for channel posts (this is key for channels!)
            elif update.channel_post:
                chat_id = update.channel_post.chat.id
                chat_type = update.channel_post.chat.type
                message_type = "unknown"
                
                if update.channel_post.video:
                    message_type = "video"
                    logger.info(f"[DEBUG] 🎬 CHANNEL POST VIDEO DETECTED! File ID: {update.channel_post.video.file_id}")
                elif update.channel_post.text:
                    message_type = "text"
                    logger.info(f"[DEBUG] 💬 CHANNEL POST TEXT: {update.channel_post.text[:50]}...")
                elif update.channel_post.photo:
                    message_type = "photo"
                elif update.channel_post.document:
                    message_type = "document"
                
                logger.info(f"[DEBUG] 📍 CHANNEL POST - Chat ID: {chat_id} | Type: {chat_type} | Content: {message_type}")
                logger.info(f"[DEBUG] 🔑 Expected private channel: {self.private_channel_id}")
                if self.private_channel_id:
                    logger.info(f"[DEBUG] 🎯 Match private channel? {chat_id == int(self.private_channel_id)}")
                
                # Process channel post videos
                if update.channel_post.video and chat_id == int(self.private_channel_id):
                    logger.info(f"[DEBUG] ✅ CHANNEL POST VIDEO FROM PRIVATE CHANNEL - PROCESSING!")
                    # Manually trigger video processing for channel posts
                    await self.handle_channel_post_video(update, context)
                elif update.channel_post.video:
                    logger.info(f"[DEBUG] ❌ Channel post video from wrong chat: {chat_id} (expected: {self.private_channel_id})")
                    
                # Log channel info if available
                if update.channel_post.chat.title:
                    logger.info(f"[DEBUG] 📋 Channel title: {update.channel_post.chat.title}")
                    
            else:
                logger.info(f"[DEBUG] ⚠️ Update with no message or channel_post: {type(update)}")
                
            logger.info(f"[DEBUG] ===== END UPDATE DEBUG =====")
                    
        except Exception as e:
            logger.error(f"Error in debug handler: {e}")

    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle Watch Now button clicks"""
        query = update.callback_query
        if not query or not query.data or not query.from_user:
            return
        await query.answer()
        
        try:
            user_id = query.from_user.id
            
            self.storage.save_user(user_id, {
                'username': query.from_user.username,
                'first_name': query.from_user.first_name
            })
            
            # Handle ad click callbacks
            if query.data.startswith('ad_click_'):
                await self.handle_ad_click(update, context)
                return
                
            # Extract video ID from callback data
            if not query.data.startswith('watch_'):
                return
            
            video_id = query.data.replace('watch_', '')
            user_id = query.from_user.id
            
            logger.info(f"User {user_id} clicked watch button for video {video_id}")
            
            # Get video data
            video_data = self.storage.get_video(video_id)
            if not video_data:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Video not found or expired."
                )
                return
            
            # Clear any previous ad completion status
            self.storage.clear_ad_completion(user_id)
            
            # Send ad with WebApp
            ad_sent, ad_id = await self.ad_manager.send_ad_to_user(context.bot, user_id, video_id)
            
            if not ad_sent:
                if ad_id == "user_not_started":
                    logger.info(f"User {user_id} needs to start the bot first")
                    try:
                        await query.answer(
                            "⚠️ Please start the bot first by clicking /start in the bot chat, then try again!",
                            show_alert=True
                        )
                    except Exception as err:
                        logger.warning(f"Cannot answer callback query for user {user_id}: {err}")
                    return
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="❌ Failed to load ad. Please try again."
                    )
                except Exception as err:
                    logger.warning(f"Cannot send error message to user {user_id}: {err}")
                return
            
            # Poll for ad completion over 60 seconds (check every 5 seconds)
            max_wait_time = 60  # Total wait time in seconds
            check_interval = 5  # Check every 5 seconds
            checks = max_wait_time // check_interval
            
            ad_completed = False
            for i in range(checks):
                await asyncio.sleep(check_interval)
                
                if self.storage.check_ad_completed(user_id, video_id):
                    ad_completed = True
                    logger.info(f"Ad completed detected for user {user_id} after {(i+1) * check_interval} seconds")
                    break
            
            if ad_completed:
                # Send the video after ad viewing time
                await self._send_video_to_user(context.bot, user_id, video_data)
                logger.info(f"Video {video_id} sent to user {user_id} after ad completion")
                
                # Clear ad completion after sending video
                self.storage.clear_ad_completion(user_id)
            else:
                # Ad was not completed within the time limit
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Ad not viewed completely. Please try again and watch the full ad."
                )
                logger.warning(f"User {user_id} did not complete ad for video {video_id} within {max_wait_time} seconds")
            
        except Exception as e:
            logger.error(f"Error handling button click: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            try:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="❌ An error occurred. Please try again later."
                )
            except:
                pass

    async def handle_ad_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle ad button clicks"""
        query = update.callback_query
        if not query or not query.data or not query.from_user:
            logger.warning("Invalid query in ad click handler")
            return
        
        await query.answer()  # Acknowledge the button click
        
        try:
            user_id = query.from_user.id
            logger.info(f"[AD_CLICK_DEBUG] Processing ad click for user {user_id}")
            logger.info(f"[AD_CLICK_DEBUG] Callback data: {query.data}")
            
            # Parse callback data: ad_click_adid_userid
            callback_parts = query.data.split('_')
            logger.info(f"[AD_CLICK_DEBUG] Callback parts: {callback_parts}")
            
            if len(callback_parts) < 4:
                logger.warning(f"[AD_CLICK_DEBUG] Invalid callback data format: {callback_parts}")
                await query.answer("Invalid ad data!", show_alert=True)
                return
                
            ad_id = callback_parts[2]
            logger.info(f"[AD_CLICK_DEBUG] Extracted ad_id: {ad_id}")
            
            # Get the ad to find the URL
            ad = self.ad_manager.get_ad(ad_id)
            logger.info(f"[AD_CLICK_DEBUG] Retrieved ad: {ad}")
            
            if not ad:
                logger.warning(f"[AD_CLICK_DEBUG] Ad not found for id: {ad_id}")
                await query.answer("Ad not found!", show_alert=True)
                return
                
            if 'url' not in ad:
                logger.warning(f"[AD_CLICK_DEBUG] Ad has no URL: {ad}")
                await query.answer("Ad link not found!", show_alert=True)
                return
            
            # Get user state to find pending video
            user_states = self.storage.get_user_states()
            user_state = user_states.get(str(user_id), {})
            pending_video_id = user_state.get('pending_video_id')
            
            logger.info(f"[AD_CLICK_DEBUG] User states: {user_states}")
            logger.info(f"[AD_CLICK_DEBUG] User state for {user_id}: {user_state}")
            logger.info(f"[AD_CLICK_DEBUG] Pending video ID: {pending_video_id}")
            
            if not pending_video_id:
                logger.warning(f"[AD_CLICK_DEBUG] No pending video for user {user_id}")
                await query.answer("No pending video found. Please try again!", show_alert=True)
                return
            
            # Edit the ad message to show the clickable link
            try:
                new_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Open Offer", url=ad['url'])]
                ])
                
                await query.edit_message_text(
                    text="📢 Advertisement\n\n💎 Click below to view the exclusive offer!\n\n⏳ Your video will be sent after viewing the ad...",
                    reply_markup=new_keyboard
                )
            except:
                pass
            
            # Send the video immediately (user engaged with ad)
            video_data = self.storage.get_video(pending_video_id)
            if video_data:
                await self._send_video_to_user(context.bot, user_id, video_data)
                
                # Clean up user state
                if str(user_id) in user_states:
                    del user_states[str(user_id)]
                    self.storage.save_user_states(user_states)
                    
                logger.info(f"Video {pending_video_id} sent to user {user_id} after ad engagement")
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Video not found. Please try again."
                )
            
        except Exception as e:
            logger.error(f"Error handling ad click: {e}")
            logger.error(f"Ad click exception details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Ad click traceback: {traceback.format_exc()}")
            try:
                await query.answer("Error processing ad click. Please try again.", show_alert=True)
            except:
                pass

    async def _send_video_to_user(self, bot, user_id: int, video_data: dict):
        """Send video to user's DM"""
        try:
            # Send video with caption
            message = await bot.send_video(
                chat_id=user_id,
                video=video_data['file_id'],
                caption=f"🎬 Enjoy your video!\n\n⏰ This message will be deleted in 24 hours.",
                supports_streaming=True
            )
            
            # Track video message for deletion after 24 hours
            # Video messages are marked as is_video=True so they won't be deleted immediately
            await self.message_manager.track_and_schedule_deletion(
                context=None,
                user_id=user_id,
                message_id=message.message_id,
                delete_previous=True,
                bot=bot,
                is_video=True
            )
            
            logger.info(f"Video {video_data['id']} sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending video to user {user_id}: {e}")
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="❌ Failed to send video. Please try again."
                )
            except:
                pass

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Bot error: {context.error}")
        
        # Try to inform user about error if update is available
        if update and hasattr(update, 'effective_user') and hasattr(update, 'effective_user'):
            try:
                effective_user = getattr(update, 'effective_user', None)
                if effective_user:
                    await context.bot.send_message(
                        chat_id=effective_user.id,
                        text="❌ An unexpected error occurred. Please try again."
                    )
            except:
                pass

    async def initialize_bot(self):
        """Initialize the bot and set up webhook"""
        try:
            logger.info("Bot initializing...")
            await self.application.initialize()
            await self.application.start()
            
            # Set bot instance for message manager
            self.message_manager.set_bot(self.application.bot)
            
            # Start background tasks
            asyncio.create_task(self.message_manager.start_cleanup_scheduler())
            
            # Test bot permissions in channels
            try:
                # Get bot info
                bot_info = await self.application.bot.get_me()
                logger.info(f"Bot info: @{bot_info.username} (ID: {bot_info.id})")
                
                # Test access to private channel
                if self.private_channel_id:
                    try:
                        private_chat = await self.application.bot.get_chat(int(self.private_channel_id))
                        logger.info(f"Private channel access OK: {private_chat.title}")
                        
                        # Check bot permissions in private channel
                        try:
                            bot_member = await self.application.bot.get_chat_member(int(self.private_channel_id), self.application.bot.id)
                            logger.info(f"Bot status in private channel: {bot_member.status}")
                            logger.info(f"Bot permissions: {bot_member}")
                        except Exception as perm_e:
                            logger.error(f"Cannot check bot permissions in private channel: {perm_e}")
                        
                    except Exception as e:
                        logger.error(f"Cannot access private channel {self.private_channel_id}: {e}")
                
                # Test access to public channel
                if self.public_channel_id:
                    try:
                        public_chat = await self.application.bot.get_chat(int(self.public_channel_id))
                        logger.info(f"Public channel access OK: {public_chat.title}")
                        
                        # Check bot permissions in public channel
                        try:
                            bot_member = await self.application.bot.get_chat_member(int(self.public_channel_id), self.application.bot.id)
                            logger.info(f"Bot status in public channel: {bot_member.status}")
                        except Exception as perm_e:
                            logger.error(f"Cannot check bot permissions in public channel: {perm_e}")
                            
                    except Exception as e:
                        logger.error(f"Cannot access public channel {self.public_channel_id}: {e}")
                    
            except Exception as e:
                logger.error(f"Error testing bot permissions: {e}")
            
            # Set webhook URL
            webhook_url = os.getenv('WEBHOOK_URL')
            if webhook_url:
                logger.info(f"Setting webhook URL: {webhook_url}")
                await self.application.bot.set_webhook(
                    url=f"{webhook_url}/webhook",
                    allowed_updates=["message", "callback_query", "channel_post", "edited_channel_post"]
                )
                logger.info("Webhook set successfully")
            else:
                logger.warning("WEBHOOK_URL not set, bot will not receive updates")
            
            logger.info("Bot initialized and ready")
                
        except Exception as e:
            logger.error(f"Error initializing bot: {e}")
            raise
    
    async def process_update(self, update_data):
        """Process an incoming update from Telegram webhook"""
        try:
            update = Update.de_json(update_data, self.application.bot)
            
            # Debug: Log channel_post details
            if update.channel_post:
                chat_id = update.channel_post.chat.id if update.channel_post.chat else None
                logger.info(f"📺 CHANNEL_POST DEBUG - Chat ID: {chat_id}, Private Channel ID: {self.private_channel_id}")
                logger.info(f"   Has video: {update.channel_post.video is not None}")
                logger.info(f"   Has document: {update.channel_post.document is not None}")
                logger.info(f"   Has photo: {update.channel_post.photo is not None if hasattr(update.channel_post, 'photo') else False}")
                logger.info(f"   Has animation: {update.channel_post.animation is not None if hasattr(update.channel_post, 'animation') else False}")
                if update.channel_post.document:
                    logger.info(f"   Document mime_type: {update.channel_post.document.mime_type}")
            
            await self.application.process_update(update)
            logger.info(f"Successfully processed update: {update_data.get('update_id', 'unknown')}")
        except Exception as e:
            logger.error(f"Error processing update {update_data.get('update_id', 'unknown')}: {e}", exc_info=True)
            raise
