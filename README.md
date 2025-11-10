# Telegram Video Sharing Bot

A Telegram bot that manages video content between private and public channels with an integrated advertisement(monetag) system.

## Features

- Video sharing from private to public channels
- Integrated advertisement system with MonetaTag
- Automatic message cleanup (24-hour auto-deletion)
- User tracking and analytics
- Web interface for ad display

## Deployment on Render (Recommended)

This bot is configured to run on Render's free plan. Follow these steps:

### 1. Prerequisites

- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A private channel ID (numeric, e.g., `-1000000000`)
- A public channel ID (numeric, e.g., `-100000000`)
- Your Telegram user ID (optional, for admin commands)

### 2. Get Channel IDs

To get the numeric channel IDs:
https://t.me/JsonDumpBot

### 3. Deploy to Render

1. **Connect your GitHub repository to Render:**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Render will automatically detect the `render.yaml` file**
   - The configuration is already set up for you
   - Build command: `pip install -r requirements.txt`
   - Start command (Production): `gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT --timeout 120`
   - Alternative (Development): `python main.py`

3. **Add Environment Variables in Render:**
   - Go to your service's "Environment" tab
   - Add these variables:
     - `BOT_TOKEN` - Your bot token from @BotFather
     - `PRIVATE_CHANNEL_ID` - Your private channel numeric ID
     - `PUBLIC_CHANNEL_ID` - Your public channel numeric ID
     - `OWNER_ID` - Your Telegram user ID (optional)
     - 'WEBHOOK_URL' - render project url

4. **Deploy:**
   - Click "Manual Deploy" → "Deploy latest commit"
   - Wait for the deployment to complete
   - Your bot will be online 24/7!

### 4. Verify Deployment

Once deployed, check the logs in Render to ensure:
- The Flask server is running
- The Telegram bot has connected successfully
- No errors appear in the logs

## Project Structure

```
.
├── main.py                 # Main entry point
├── bot_handler.py         # Telegram bot handler
├── video_processor.py     # Video processing logic
├── ad_manager.py          # Advertisement management
├── message_manager.py     # Message cleanup system
├── storage.py             # JSON-based data storage
├── static/                # Static files (HTML, CSS, JS)
├── data/                  # Bot data (created automatically)
├── requirements.txt       # Python dependencies
└── render.yaml           # Render configuration
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Your Telegram bot token |
| `PRIVATE_CHANNEL_ID` | Yes | Numeric ID of private channel |
| `PUBLIC_CHANNEL_ID` | Yes | Numeric ID of public channel |
| `OWNER_ID` | No | Your Telegram user ID for admin features |
| `PORT` | Auto | Set automatically by Render |

## Bot Commands

- `/start` - Start the bot and get welcome message
- `/help` - Get help information
- `/stats` - View bot statistics (owner only)

## Local Development

To run locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BOT_TOKEN="your_bot_token"
export PRIVATE_CHANNEL_ID="-100000000"
export PUBLIC_CHANNEL_ID="-100000000"
export OWNER_ID="your_user_id"

# Run the bot
python main.py
```

## Troubleshooting

### Bot not starting on Render
- Check that all required environment variables are set
- Verify your bot token is correct
- Ensure channel IDs are numeric (not usernames)

### Videos not being shared
- Make sure the bot is an admin in both channels
- Check that channel IDs are correct (use negative numbers)
- Verify the bot has permission to post in the public channel

### Ads not displaying
- Check the Render logs for any errors
- Ensure the Flask server is running (check `/health` endpoint)
- Verify the MonetaTag SDK is loading correctly

## Support

For issues or questions, check the Render deployment logs for error messages.

## License

This project is open source and available for personal and commercial use.
