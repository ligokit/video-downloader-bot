"""
Script to set Telegram webhook for Vercel deployment.
Run this after deploying to Vercel.
"""
import os
import sys
import asyncio
from aiogram import Bot
from dotenv import load_dotenv

load_dotenv()


async def set_webhook(webhook_url: str):
    """Set webhook URL for the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in environment")
        sys.exit(1)
    
    bot = Bot(token=token)
    
    try:
        # Delete existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Deleted existing webhook")
        
        # Set new webhook
        webhook_info = await bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )
        
        if webhook_info:
            print(f"✅ Webhook set successfully!")
            print(f"   URL: {webhook_url}")
            
            # Get webhook info
            info = await bot.get_webhook_info()
            print(f"\n📊 Webhook Info:")
            print(f"   URL: {info.url}")
            print(f"   Pending updates: {info.pending_update_count}")
            if info.last_error_message:
                print(f"   Last error: {info.last_error_message}")
        else:
            print("❌ Failed to set webhook")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    finally:
        await bot.session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_webhook.py <your-vercel-url>")
        print("Example: python set_webhook.py https://your-app.vercel.app/api/webhook")
        sys.exit(1)
    
    webhook_url = sys.argv[1]
    
    if not webhook_url.startswith("https://"):
        print("❌ Error: Webhook URL must use HTTPS")
        sys.exit(1)
    
    print(f"🔧 Setting webhook to: {webhook_url}")
    asyncio.run(set_webhook(webhook_url))
