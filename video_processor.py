"""
Video processor for extracting thumbnails and managing video data
"""

import logging
import uuid
from datetime import datetime
from telegram import Bot, Video, Message
from storage import Storage

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, storage: Storage):
        self.storage = storage

    async def process_video(self, bot: Bot, video: Video, message: Message) -> dict:
        """
        Process video from private channel and extract thumbnail
        
        Args:
            bot: Telegram bot instance
            video: Video object from Telegram
            message: Message containing the video
            
        Returns:
            dict: Video data with thumbnail info and downloadable thumbnail
        """
        try:
            # Generate unique video ID
            video_id = str(uuid.uuid4())[:8]
            
            # Download and get thumbnail as bytes for re-uploading
            thumbnail_file_id = None
            thumbnail_bytes = None
            if video.thumbnail:
                try:
                    # Download the thumbnail
                    thumbnail_file = await bot.get_file(video.thumbnail.file_id)
                    thumbnail_bytes = await thumbnail_file.download_as_bytearray()
                    thumbnail_file_id = video.thumbnail.file_id
                    logger.info(f"Thumbnail downloaded for video {video_id} ({len(thumbnail_bytes)} bytes)")
                except Exception as thumb_error:
                    logger.warning(f"Failed to download thumbnail for video {video_id}: {thumb_error}")
            else:
                logger.warning(f"No thumbnail found for video {video_id}")
            
            # Get original caption and entities (for formatting preservation)
            caption = message.caption or message.caption_html or ""
            caption_entities = message.caption_entities if message.caption_entities else []
            
            # Create video data (don't store thumbnail_bytes to avoid serialization issues)
            video_data = {
                'id': video_id,
                'file_id': video.file_id,
                'file_unique_id': video.file_unique_id,
                'thumbnail_file_id': thumbnail_file_id,
                'duration': video.duration,
                'width': video.width,
                'height': video.height,
                'file_size': video.file_size,
                'mime_type': video.mime_type,
                'file_name': video.file_name or f"video_{video_id}",
                'uploaded_at': datetime.now().isoformat(),
                'message_id': message.message_id,
                'caption': caption,
                'caption_entities': [
                    {
                        'type': entity.type,
                        'offset': entity.offset,
                        'length': entity.length,
                        'url': entity.url if hasattr(entity, 'url') else None
                    } for entity in caption_entities
                ]
            }
            
            # Store video data (without thumbnail_bytes)
            self.storage.save_video(video_data)
            
            # Add thumbnail_bytes to return data for immediate use (not persisted)
            video_data['thumbnail_bytes'] = thumbnail_bytes
            
            logger.info(f"Video processed successfully: {video_id}")
            return video_data
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return {}

    def get_video_info(self, video_id: str) -> dict:
        """Get video information by ID"""
        return self.storage.get_video(video_id)

    def list_videos(self) -> list:
        """List all processed videos"""
        return list(self.storage.get_videos().values())

    def delete_video(self, video_id: str) -> bool:
        """Delete video from storage"""
        try:
            self.storage.delete_video(video_id)
            logger.info(f"Video deleted: {video_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting video {video_id}: {e}")
            return False

    async def get_video_statistics(self) -> dict:
        """Get video processing statistics"""
        videos = self.storage.get_videos()
        
        total_videos = len(videos)
        videos_with_thumbnails = sum(1 for v in videos.values() if v.get('thumbnail_file_id'))
        
        # Calculate total file size
        total_size = sum(v.get('file_size', 0) for v in videos.values() if v.get('file_size'))
        
        # Get most recent video
        most_recent = None
        if videos:
            most_recent = max(videos.values(), key=lambda v: v['uploaded_at'])
        
        return {
            'total_videos': total_videos,
            'videos_with_thumbnails': videos_with_thumbnails,
            'total_file_size_bytes': total_size,
            'most_recent_video': most_recent['uploaded_at'] if most_recent else None
        }
