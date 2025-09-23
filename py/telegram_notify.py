#!/usr/bin/env python3
"""
Simple Telegram notifier for GitHub Actions
"""
import requests
import os
import sys

def send_telegram_message(title, message):
    # TOKEN dan CHAT_ID langsung ditulis di sini
    BOT_TOKEN = "7732517146:AAFxfT074Ma8kzWPWFXZgTR978hCAat-c0U"  # Ganti dengan token bot Anda
    CHAT_ID = "7121031492"                       # Ganti dengan chat ID Anda
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': CHAT_ID,
        'text': f"<b>{title}</b>\n{message}",
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Notification sent: {title}")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notification failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        title = sys.argv[1]
        message = sys.argv[2]
        send_telegram_message(title, message)
    else:
        print("Usage: python telegram_notify.py 'Title' 'Message'")