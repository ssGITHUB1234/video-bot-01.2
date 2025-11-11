# Overview
This project is a Telegram video sharing bot designed to manage video content between private and public channels, integrating an advertisement system. Its core purpose is to process videos uploaded to a private channel, display video thumbnails with original captions to users in a public channel, and deliver the full video after users watch advertisements. The bot preserves all caption formatting (bold, italic, links, etc.) and manages automatic message cleanup. The bot aims to provide a robust and scalable solution for content distribution with monetization capabilities.

# Recent Changes
## November 11, 2025 - Replit Import & Ad System Update
- **Replit Environment Setup**: Configured project to run in Replit environment
  - Installed all required Python dependencies (bcrypt, psycopg2-binary, gunicorn, Flask, etc.)
  - Configured Flask workflow to run on port 5000 with host 0.0.0.0 for proper web preview
  - Set up deployment configuration using Gunicorn with VM target for webhook support
  - Created .gitignore for Python project
  - PostgreSQL database auto-configured via Replit's DATABASE_URL
- **Ad System Migration**: Switched from Monetag rewarded interstitial ads to rewarded popup ads
  - Updated static/ad.html to use `show_XXX({ type: 'pop' })` for popup-based ads
  - Implemented button-triggered ad flow: user clicks → popup opens externally → 15s verification → video delivery
  - Added countdown timer with proper reset on retry attempts
  - Improved UX with loading states, status messages, and visual feedback
  - Maintained tracking with `ymid` parameter for user identification
  - Added graceful fallback handling for ad SDK failures

## November 5, 2025 - Revenue Protection Fix
- **CRITICAL FIX**: Bot now properly sends ONLY thumbnail images to public channel (not full videos)
- Downloads and re-uploads thumbnails as photos to bypass Telegram's thumbnail file_id restriction
- Full videos are hidden and only delivered to users AFTER they watch advertisements
- Protects ad-based revenue model by preventing free video access in public channel
- Added fallback: sends text-only post if thumbnail download fails
- Fixed ad page loading crash when ad URL is None

## November 1, 2025 - Video Distribution Update
- Modified bot to send **thumbnails** (not full videos) to public channel when new videos are posted in admin channel
- Preserved all caption formatting when forwarding (bold, italic, monospace, links, etc.)
- Implemented MessageEntity reconstruction to maintain text formatting across Telegram's API
- Videos are now delivered to users only after they watch advertisements
- Updated both `handle_private_channel_video` and `handle_channel_post_video` handlers

# User Preferences
Preferred communication style: Simple, everyday language.

# System Architecture
## Bot Framework
- **Python Telegram Bot Library**: Utilizes `python-telegram-bot` for all Telegram API interactions.
- **Asynchronous Design**: Employs `async`/`await` patterns for concurrent operations.
- **Modular Architecture**: Components are separated for maintainability (bot handler, video processor, ad manager, message manager, storage).

## Core Components
- **Bot Handler**: Centralized management of Telegram interactions, commands, message processing, and callback queries. Handles forwarding video thumbnails (with original captions) to the public channel, with fallback to full video if thumbnail is unavailable. Preserves all caption formatting using MessageEntity reconstruction.
- **Video Processor**: Handles video metadata extraction, thumbnail generation, caption extraction with formatting entities (bold, italic, links, code), unique ID creation, and processing for distribution. Stores caption entities to preserve formatting when forwarding.
- **Advertisement Manager**: Manages a rotating, text-based advertisement system, including ad selection, display timing, and active/inactive states.
- **Message Manager**: Implements a 24-hour auto-deletion system for user messages, tracking their lifecycle and managing cleanup schedules.

## UI/UX Decisions
- **Admin Panel**: Web-based interface for managing ads, viewing statistics (total users, videos, active ads, ad views), and user details.
  - **Security**: Password-based authentication (`ADMIN_PASSWORD`), token-based session management, and secure logout.
  - **Features**: Add, edit, delete, and toggle ad activity; all changes apply instantly.

## Data Storage
- **Dual Storage System**: Automatically selects storage backend based on environment:
  - **PostgreSQL Mode (Production)**: Used when `DATABASE_URL` is set, leveraging Render's managed PostgreSQL for persistent data. Features connection pooling, transaction safety, automatic table initialization, and Render-managed backups.
  - **JSON Mode (Development/Testing)**: Used when `DATABASE_URL` is not set, storing data in JSON files within the `data/` directory.
- **Schema**: Data is stored across `users`, `videos`, `ads`, `messages`, `user_states`, and `admin_sessions` tables/files with indexing.

## Infrastructure
- **Webhook-Based Deployment**: Operates using webhooks for Telegram updates, suitable for cloud hosting platforms like Render.
- **Flask Web Server**: Provides HTTP endpoints:
  - `/webhook`: Receives and processes Telegram updates.
  - `/health`: For service status checks.
  - `/admin-login`: Secure access to the admin panel.
- **Concurrency**: Uses `asyncio.run_coroutine_threadsafe` for thread-safe asynchronous execution within a dedicated background thread.
- **Channel Management**: Utilizes a dual-channel system (private for intake, public for distribution) for content flow and access control.
- **Video Distribution Flow**: 
  - Videos posted in private channel are processed to extract thumbnails and captions
  - Thumbnails are posted to public channel with original captions (all formatting preserved)
  - Full videos are delivered to users only after they watch advertisements
  - Fallback mechanism sends full video if thumbnail is unavailable

# External Dependencies
- **Telegram Bot API**:
  - `python-telegram-bot` library.
  - Requires `BOT_TOKEN`, `PRIVATE_CHANNEL_ID`, `PUBLIC_CHANNEL_ID`.
- **PostgreSQL Database**:
  - Render's managed PostgreSQL (free tier).
  - Configured via `DATABASE_URL` environment variable.
- **HTTP Services**:
  - `Flask` for web server functionality.
  - `Requests` for HTTP client operations.
- **Environment Variables**:
  - `BOT_TOKEN`, `PRIVATE_CHANNEL_ID`, `PUBLIC_CHANNEL_ID`, `WEBHOOK_URL`, `ADMIN_PASSWORD`.