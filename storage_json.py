"""
JSON-based storage system for bot data (fallback for Replit development)
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class JSONStorage:
    def __init__(self):
        self.data_dir = 'data'
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.files = {
            'users': os.path.join(self.data_dir, 'users.json'),
            'videos': os.path.join(self.data_dir, 'videos.json'),
            'ads': os.path.join(self.data_dir, 'ads.json'),
            'messages': os.path.join(self.data_dir, 'messages.json'),
            'user_states': os.path.join(self.data_dir, 'user_states.json'),
            'admin_sessions': os.path.join(self.data_dir, 'admin_sessions.json')
        }
        
        # Initialize files if they don't exist
        for file_path in self.files.values():
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump({}, f)
        
        logger.info("Using JSON storage (development mode)")
    
    def _read_file(self, key: str) -> Dict:
        try:
            with open(self.files[key], 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {key}: {e}")
            return {}
    
    def _write_file(self, key: str, data: Dict):
        try:
            with open(self.files[key], 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing {key}: {e}")
    
    # Video storage methods
    def save_video(self, video_data: Dict[str, Any]):
        videos = self._read_file('videos')
        videos[video_data['id']] = video_data
        self._write_file('videos', videos)
    
    def get_video(self, video_id: str) -> Dict[str, Any]:
        videos = self._read_file('videos')
        return videos.get(video_id, {})
    
    def get_videos(self) -> Dict[str, Any]:
        return self._read_file('videos')
    
    def delete_video(self, video_id: str):
        videos = self._read_file('videos')
        if video_id in videos:
            del videos[video_id]
            self._write_file('videos', videos)
    
    # Ad storage methods
    def save_ad(self, ad_data: Dict[str, Any]):
        ads = self._read_file('ads')
        ads[ad_data['id']] = ad_data
        self._write_file('ads', ads)
    
    def get_ad(self, ad_id: str) -> Dict[str, Any]:
        ads = self._read_file('ads')
        return ads.get(ad_id, {})
    
    def get_ads(self) -> Dict[str, Any]:
        return self._read_file('ads')
    
    def delete_ad(self, ad_id: str):
        ads = self._read_file('ads')
        if ad_id in ads:
            del ads[ad_id]
            self._write_file('ads', ads)
    
    # Message tracking methods
    def save_message_tracking(self, message_key: str, message_data: Dict[str, Any]):
        messages = self._read_file('messages')
        messages[message_key] = message_data
        self._write_file('messages', messages)
    
    def get_message_tracking(self, message_key: str) -> Dict[str, Any]:
        messages = self._read_file('messages')
        return messages.get(message_key, {})
    
    def get_all_message_tracking(self) -> Dict[str, Any]:
        return self._read_file('messages')
    
    def get_user_messages(self, user_id: int) -> Dict[str, Any]:
        messages = self._read_file('messages')
        return {k: v for k, v in messages.items() if v.get('user_id') == user_id}
    
    def delete_message_tracking(self, message_key: str):
        messages = self._read_file('messages')
        if message_key in messages:
            del messages[message_key]
            self._write_file('messages', messages)
    
    # User state methods
    def save_user_state(self, user_id: int, state_data: Dict[str, Any]):
        states = self._read_file('user_states')
        states[str(user_id)] = state_data
        self._write_file('user_states', states)
    
    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        states = self._read_file('user_states')
        return states.get(str(user_id), {})
    
    def get_user_states(self) -> Dict[str, Any]:
        return self._read_file('user_states')
    
    def save_user_states(self, user_states: Dict[str, Any]):
        self._write_file('user_states', user_states)
    
    def delete_user_state(self, user_id: int):
        states = self._read_file('user_states')
        if str(user_id) in states:
            del states[str(user_id)]
            self._write_file('user_states', states)
    
    # Ad completion tracking methods
    def start_ad_session(self, user_id: int, ad_id: str, video_id: str, session_token: str):
        state_data = {
            'ad_session_token': session_token,
            'ad_session_start': datetime.now().isoformat(),
            'ad_id': ad_id,
            'video_id': video_id,
            'ad_completed': False
        }
        self.save_user_state(user_id, state_data)
    
    def mark_ad_completed(self, user_id: int, ad_id: str, video_id: str, session_token: str) -> bool:
        user_state = self.get_user_state(user_id)
        
        if not user_state:
            return False
        
        if user_state.get('ad_session_token') != session_token:
            return False
        
        if user_state.get('video_id') != video_id:
            return False
        
        state_data = {
            **user_state,
            'ad_completed': True,
            'ad_completed_at': datetime.now().isoformat()
        }
        self.save_user_state(user_id, state_data)
        return True
    
    def check_ad_completed(self, user_id: int, video_id: str) -> bool:
        user_state = self.get_user_state(user_id)
        return (user_state.get('ad_completed') == True and 
                user_state.get('video_id') == video_id)
    
    def clear_ad_completion(self, user_id: int):
        state_data = {
            'ad_completed': False,
            'ad_id': None,
            'video_id': None
        }
        self.save_user_state(user_id, state_data)
    
    # User tracking methods
    def save_user(self, user_id: int, user_data: Dict[str, Any]):
        users = self._read_file('users')
        
        if str(user_id) in users:
            users[str(user_id)]['username'] = user_data.get('username', users[str(user_id)].get('username'))
            users[str(user_id)]['first_name'] = user_data.get('first_name', users[str(user_id)].get('first_name'))
            users[str(user_id)]['last_interaction'] = datetime.now().isoformat()
            users[str(user_id)]['interaction_count'] = users[str(user_id)].get('interaction_count', 0) + 1
        else:
            users[str(user_id)] = {
                'user_id': user_id,
                'username': user_data.get('username', ''),
                'first_name': user_data.get('first_name', ''),
                'first_interaction': datetime.now().isoformat(),
                'last_interaction': datetime.now().isoformat(),
                'interaction_count': 1
            }
        
        self._write_file('users', users)
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        users = self._read_file('users')
        return users.get(str(user_id), {})
    
    def get_all_users(self) -> Dict[str, Any]:
        return self._read_file('users')
    
    def get_user_count(self) -> int:
        users = self._read_file('users')
        return len(users)
    
    # Admin session methods
    def create_admin_session(self, token: str, created_at: float, last_activity: float):
        sessions = self._read_file('admin_sessions')
        sessions[token] = {
            'created_at': created_at,
            'last_activity': last_activity
        }
        self._write_file('admin_sessions', sessions)
    
    def update_admin_session_activity(self, token: str, last_activity: float) -> bool:
        sessions = self._read_file('admin_sessions')
        if token in sessions:
            sessions[token]['last_activity'] = last_activity
            self._write_file('admin_sessions', sessions)
            return True
        return False
    
    def get_all_admin_sessions(self) -> Dict[str, Dict[str, Any]]:
        return self._read_file('admin_sessions')
    
    def delete_admin_session(self, token: str):
        sessions = self._read_file('admin_sessions')
        if token in sessions:
            del sessions[token]
            self._write_file('admin_sessions', sessions)
    
    def get_storage_stats(self) -> Dict[str, Any]:
        return {
            'users_count': len(self._read_file('users')),
            'videos_count': len(self._read_file('videos')),
            'ads_count': len(self._read_file('ads')),
            'messages_count': len(self._read_file('messages')),
            'user_states_count': len(self._read_file('user_states')),
            'admin_sessions_count': len(self._read_file('admin_sessions')),
            'storage_type': 'JSON (Development)',
            'database_url': 'N/A'
        }
    
    def backup_data(self) -> str:
        return "JSON files are used - no backup needed"
    
    def restore_from_backup(self, backup_path: str) -> bool:
        return False
