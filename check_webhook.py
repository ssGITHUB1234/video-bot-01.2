#!/usr/bin/env python3
"""
Webhook Diagnostic Tool
Run this to check if your webhook is properly configured
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_webhook():
    bot_token = os.getenv('BOT_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables")
        return
    
    print(f"✅ BOT_TOKEN found: {bot_token[:10]}...")
    
    if not webhook_url:
        print("⚠️  WEBHOOK_URL not set in environment variables")
        print("   This should be your Render service URL (e.g., https://your-app.onrender.com)")
    else:
        print(f"✅ WEBHOOK_URL set: {webhook_url}")
    
    # Check current webhook info
    print("\n🔍 Checking current webhook configuration with Telegram...")
    
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo")
        data = response.json()
        
        if data.get('ok'):
            info = data.get('result', {})
            print("\n📊 Current Webhook Info:")
            print(f"   URL: {info.get('url', 'NOT SET')}")
            print(f"   Has Custom Certificate: {info.get('has_custom_certificate', False)}")
            print(f"   Pending Update Count: {info.get('pending_update_count', 0)}")
            print(f"   Max Connections: {info.get('max_connections', 'N/A')}")
            
            if info.get('last_error_date'):
                print(f"\n⚠️  Last Error Date: {info.get('last_error_date')}")
                print(f"   Last Error Message: {info.get('last_error_message', 'N/A')}")
            
            if info.get('url'):
                print(f"\n✅ Webhook is SET: {info.get('url')}")
                if webhook_url and info.get('url') == f"{webhook_url}/webhook":
                    print("✅ Webhook URL matches your WEBHOOK_URL environment variable")
                elif webhook_url:
                    print(f"❌ Webhook URL mismatch!")
                    print(f"   Expected: {webhook_url}/webhook")
                    print(f"   Actual:   {info.get('url')}")
            else:
                print("\n❌ Webhook is NOT SET!")
                print("   Bot will not receive updates until webhook is configured")
        else:
            print(f"❌ Error checking webhook: {data}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Suggest next steps
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    
    if not webhook_url:
        print("1. Set WEBHOOK_URL environment variable on Render")
        print("   Example: https://your-app-name.onrender.com")
        print("2. Redeploy your service on Render")
    else:
        print("1. Make sure WEBHOOK_URL is set on Render (not just locally)")
        print("2. After deploying, the bot should set the webhook automatically")
        print("3. If webhook is still not set, you may need to set it manually")
        print("\nTo manually set webhook, run:")
        print(f'curl -X POST "https://api.telegram.org/bot{bot_token[:10]}...YOUR_FULL_TOKEN/setWebhook?url={webhook_url}/webhook"')

if __name__ == '__main__':
    check_webhook()
