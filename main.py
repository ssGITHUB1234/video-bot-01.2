#!/usr/bin/env python3
"""
Telegram Bot for Video Sharing with Ad System
Main entry point for the bot application
"""

import os
import logging
import asyncio
import threading
import secrets
import bcrypt
from flask import Flask, request, jsonify, send_file, redirect
from bot_handler import TelegramBotHandler
from storage import Storage

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global bot handler instance
bot_handler = None
loop = None
loop_thread = None

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
storage = Storage()

# Admin sessions cache (loaded from database)
admin_sessions = {}

def run_event_loop(loop):
    """Run the event loop in a background thread"""
    asyncio.set_event_loop(loop)
    logger.info("Event loop thread started and running")
    
    async def keep_alive():
        """Keep the event loop alive indefinitely"""
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour, repeat forever
    
    try:
        # Schedule keep_alive task to prevent event loop from stopping
        loop.create_task(keep_alive())
        loop.run_forever()
    except Exception as e:
        logger.error(f"Event loop crashed: {e}", exc_info=True)
    finally:
        logger.warning("Event loop stopped running")

@app.route('/')
def home():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(base_dir, 'static', 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading index.html: {e}")
        return "Telegram Video Bot is running", 200

@app.route('/health')
def health():
    bot_status = 'running' if bot_handler and hasattr(bot_handler, 'application') else 'starting'
    return {'status': 'alive', 'bot': bot_status}

@app.route('/ad-redirect')
def ad_redirect():
    """Redirect to ad page with user session setup"""
    try:
        import secrets
        from ad_manager import AdManager
        
        video_id = request.args.get('video_id', '')
        user_id = request.args.get('user_id', '')
        
        if not user_id:
            # Get user_id from Telegram WebApp context
            return """
            <html>
            <head>
                <script src="https://telegram.org/js/telegram-web-app.js"></script>
                <script>
                    const tg = window.Telegram.WebApp;
                    tg.ready();
                    const userId = tg.initDataUnsafe?.user?.id;
                    if (userId) {
                        window.location.href = window.location.pathname + '?video_id=""" + video_id + """&user_id=' + userId;
                    } else {
                        document.body.innerHTML = '<div style="text-align:center;padding:40px;font-family:sans-serif;"><h2>❌ Error</h2><p>Please open this from Telegram</p></div>';
                    }
                </script>
            </head>
            <body><p style="text-align:center;padding:40px;">Loading...</p></body>
            </html>
            """
        
        # Get next ad
        ad_manager = AdManager(storage)
        ad = ad_manager.get_next_ad()
        
        if not ad:
            return "<p style='text-align:center;padding:20px;'>No ads available</p>", 500
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        
        # Start ad session
        storage.start_ad_session(int(user_id), ad['id'], video_id, session_token)
        
        # Redirect to actual ad page
        return redirect(f'/ad?user_id={user_id}&ad_id={ad["id"]}&video_id={video_id}&token={session_token}')
        
    except Exception as e:
        logger.error(f"Error in ad redirect: {e}")
        return f"<p style='text-align:center;padding:20px;'>Error: {e}</p>", 500

@app.route('/ad')
def ad_page():
    user_id = request.args.get('user_id')
    ad_id = request.args.get('ad_id')
    video_id = request.args.get('video_id')
    token = request.args.get('token')
    
    if not user_id or not ad_id or not video_id or not token:
        logger.warning(f"Invalid ad page parameters: user_id={user_id}, ad_id={ad_id}, video_id={video_id}, token={token}")
        return "Invalid parameters", 400
    
    ad = storage.get_ad(ad_id)
    ad_url = ad.get('url') if ad else None
    # Ensure ad_url is always a string (handle None case)
    if ad_url is None:
        ad_url = ''
    
    try:
        # Get the directory where main.py is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ad_html_path = os.path.join(base_dir, 'static', 'ad.html')
        
        logger.info(f"Reading ad.html from: {ad_html_path}")
        logger.info(f"File exists: {os.path.exists(ad_html_path)}")
        
        with open(ad_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return html_content.replace(
            '{{USER_ID}}', user_id
        ).replace(
            '{{AD_ID}}', ad_id
        ).replace(
            '{{VIDEO_ID}}', video_id
        ).replace(
            '{{TOKEN}}', token
        ).replace(
            '{{AD_URL}}', ad_url
        )
    except Exception as e:
        logger.error(f"Error reading ad.html: {e}", exc_info=True)
        logger.error(f"Current working directory: {os.getcwd()}")
        logger.error(f"Directory contents: {os.listdir(os.getcwd())}")
        return f"Ad page unavailable: {str(e)}", 500

@app.route('/complete-ad', methods=['POST'])
def complete_ad():
    data = request.json if request.json else {}
    user_id = data.get('user_id')
    ad_id = data.get('ad_id')
    video_id = data.get('video_id')
    token = data.get('token')
    
    if not user_id or not ad_id or not video_id or not token:
        return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
    
    try:
        success = storage.mark_ad_completed(int(user_id), ad_id, video_id, token)
        
        if success:
            return jsonify({'success': True, 'message': 'Ad completed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Invalid session or time not elapsed'}), 403
    except Exception as e:
        logger.error(f"Error marking ad as completed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming updates from Telegram"""
    global bot_handler, loop, loop_thread
    
    # Check event loop thread health
    if loop_thread and not loop_thread.is_alive():
        logger.error("Event loop thread is DEAD!")
        return jsonify({'error': 'Event loop crashed'}), 503
    
    logger.info(f"Webhook called - bot_handler exists: {bot_handler is not None}, loop exists: {loop is not None}, loop running: {loop.is_running() if loop else False}")
    
    if not bot_handler or not loop:
        logger.error(f"Bot handler not initialized - bot_handler: {bot_handler}, loop: {loop}")
        return jsonify({'error': 'Bot not ready'}), 503
    
    try:
        update_data = request.get_json(force=True)
        update_id = update_data.get('update_id', 'unknown')
        logger.info(f"Received webhook update: {update_id}")
        logger.info(f"Update data keys: {list(update_data.keys())}")
        
        # Process update asynchronously in the event loop thread
        try:
            # Use a simple coroutine to test event loop responsiveness
            async def test_and_process():
                logger.info(f"Event loop processing update {update_id}")
                await bot_handler.process_update(update_data)
                logger.info(f"Event loop finished processing update {update_id}")
            
            future = asyncio.run_coroutine_threadsafe(test_and_process(), loop)
            logger.info(f"Update {update_id} submitted to event loop")
            
            # Add callback to log result
            def log_result(fut):
                try:
                    fut.result()  # Get result or raise exception
                    logger.info(f"✅ Update {update_id} processed successfully")
                except Exception as e:
                    logger.error(f"❌ Update {update_id} processing failed: {e}", exc_info=True)
            
            future.add_done_callback(log_result)
        except Exception as submit_error:
            logger.error(f"Failed to submit update {update_id} to event loop: {submit_error}", exc_info=True)
            return jsonify({'error': str(submit_error)}), 500
        
        # Return immediately to prevent Gunicorn worker timeouts
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Admin authentication helper
def verify_admin_token(token):
    """Verify admin token and return True if valid"""
    # Update last activity timestamp if session exists
    # This will return False if session was deleted (logged out)
    return storage.update_admin_session_activity(token, os.times().elapsed)

# Admin routes
@app.route('/admin-login')
def admin_login_page():
    try:
        return open('static/admin-login.html').read()
    except Exception as e:
        logger.error(f"Error reading admin-login.html: {e}")
        return "Admin login page unavailable", 500

@app.route('/admin')
def admin_panel():
    try:
        return open('static/admin.html').read()
    except Exception as e:
        logger.error(f"Error reading admin.html: {e}")
        return "Admin panel unavailable", 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json if request.json else {}
    password = data.get('password')
    
    if not password:
        return jsonify({'success': False, 'error': 'Password required'}), 400
    
    try:
        # Get admin password from environment
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        if not admin_password:
            return jsonify({'success': False, 'error': 'Admin access not configured. Please set ADMIN_PASSWORD environment variable.'}), 403
        
        # Verify password
        if password != admin_password:
            logger.warning("Failed admin login attempt")
            return jsonify({'success': False, 'error': 'Invalid password'}), 403
        
        # Generate session token
        token = secrets.token_urlsafe(32)
        current_time = os.times().elapsed
        
        # Create new session in database
        storage.create_admin_session(token, current_time, current_time)
        
        logger.info("Admin logged in successfully")
        return jsonify({'success': True, 'token': token})
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = auth_header.replace('Bearer ', '')
    if not verify_admin_token(token):
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        users = storage.get_all_users()
        videos = storage.get_videos()
        ads = storage.get_ads()
        
        active_ads = [ad for ad in ads.values() if ad.get('active', True)]
        total_ad_views = sum(ad.get('views', 0) for ad in ads.values())
        
        return jsonify({
            'total_users': len(users),
            'total_videos': len(videos),
            'active_ads': len(active_ads),
            'total_ad_views': total_ad_views
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = auth_header.replace('Bearer ', '')
    if not verify_admin_token(token):
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        users = storage.get_all_users()
        user_list = []
        
        for user_id, user_data in users.items():
            user_list.append({
                'user_id': user_id,
                'username': user_data.get('username'),
                'first_name': user_data.get('first_name'),
                'joined_at': user_data.get('joined_at', user_data.get('first_interaction', user_data.get('created_at', '')))
            })
        
        # Sort by joined_at descending
        user_list.sort(key=lambda x: x.get('joined_at', ''), reverse=True)
        
        return jsonify({'users': user_list})
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/ads', methods=['GET', 'POST'])
def manage_ads():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = auth_header.replace('Bearer ', '')
    if not verify_admin_token(token):
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        if request.method == 'GET':
            ads = storage.get_ads()
            ad_list = list(ads.values())
            ad_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return jsonify({'ads': ad_list})
        
        elif request.method == 'POST':
            ad_data = request.json
            if not ad_data or not ad_data.get('content'):
                return jsonify({'success': False, 'error': 'Ad content required'}), 400
            
            # Use existing ad manager to add/update ad
            from ad_manager import AdManager
            ad_manager = AdManager(storage)
            
            if ad_data.get('id'):
                # Update existing ad
                ad = storage.get_ad(ad_data['id'])
                if ad:
                    ad.update({
                        'type': ad_data.get('type', 'text'),
                        'content': ad_data['content'],
                        'duration': ad_data.get('duration', 60),
                        'active': ad_data.get('active', True)
                    })
                    storage.save_ad(ad)
                    return jsonify({'success': True, 'ad_id': ad['id']})
                else:
                    return jsonify({'success': False, 'error': 'Ad not found'}), 404
            else:
                # Add new ad
                ad_id = ad_manager.add_ad(ad_data)
                if ad_id:
                    return jsonify({'success': True, 'ad_id': ad_id})
                else:
                    return jsonify({'success': False, 'error': 'Failed to create ad'}), 500
    
    except Exception as e:
        logger.error(f"Error managing ads: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/ads/<ad_id>', methods=['DELETE'])
def delete_ad(ad_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = auth_header.replace('Bearer ', '')
    if not verify_admin_token(token):
        return jsonify({'error': 'Invalid token'}), 401
    
    try:
        from ad_manager import AdManager
        ad_manager = AdManager(storage)
        success = ad_manager.delete_ad(ad_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Ad not found'}), 404
    
    except Exception as e:
        logger.error(f"Error deleting ad: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """Logout admin and invalidate session token"""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '')
        # Delete session from database
        storage.delete_admin_session(token)
        logger.info("Admin logged out successfully")
    
    return jsonify({'success': True})

def initialize_bot():
    """Initialize the Telegram bot at startup"""
    global bot_handler, loop, loop_thread
    try:
        # Create and start event loop in background thread
        logger.info("Starting event loop in background thread...")
        loop = asyncio.new_event_loop()
        loop_thread = threading.Thread(target=run_event_loop, args=(loop,), daemon=True)
        loop_thread.start()
        
        # Give event loop thread time to start
        import time
        time.sleep(0.5)
        
        if not loop_thread.is_alive():
            raise RuntimeError("Event loop thread failed to start")
        
        logger.info("Initializing Telegram bot...")
        bot_handler = TelegramBotHandler()
        
        logger.info("Setting up bot webhook...")
        future = asyncio.run_coroutine_threadsafe(bot_handler.initialize_bot(), loop)
        result = future.result(timeout=30)
        logger.info("Bot initialized successfully")
        
        # Verify event loop is still running
        if not loop_thread.is_alive():
            logger.error("Event loop thread died during bot initialization!")
            raise RuntimeError("Event loop thread died")
        
        logger.info(f"Event loop thread status: alive={loop_thread.is_alive()}, loop running={loop.is_running()}")
        
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}", exc_info=True)
        logger.warning("Bot initialization failed, but Flask server will continue to run for admin access")
        # Don't raise - allow Flask to continue for admin dashboard access

def main():
    """Main function to start the bot and Flask server"""
    try:
        # Initialize bot at startup (optional - Flask will run even if bot fails)
        initialize_bot()
        
        # Start Flask server
        port = int(os.getenv('PORT', 5000))
        logger.info(f"Starting Flask server on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed with error: {e}")
        if "Bot" not in str(e):
            raise

if __name__ == '__main__':
    main()
