from flask import Flask, request, jsonify
from telethon import TelegramClient
import asyncio
import os

app = Flask(__name__)

# Your credentials
api_id = 39955957
api_hash = "03ecd7b069da3c4da117f1d21ac14f54"
phone = "+923368554422"

# Initialize client once
client = TelegramClient('session_name', api_id, api_hash)

async def send_telegram_message(group, message):
    """Send message to Telegram group"""
    if not client.is_connected():
        await client.connect()
        if not await client.is_user_authorized():
            await client.start(phone=phone)
    
    await client.send_message(group, message)
    return True

@app.route('/send-message', methods=['POST'])
def send_message():
    """Endpoint to send Telegram messages"""
    try:
        data = request.get_json()
        
        # Get group and message from request, or use defaults
        group = data.get('group', 'https://t.me/+obmFfJdYLWIwYjk0')
        message = data.get('message', 'This is an automated message.')
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_telegram_message(group, message))
        loop.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Message sent successfully!'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

async def initialize_client():
    """Initialize and authenticate the Telegram client"""
    await client.start(phone=phone)
    print("Telegram client authenticated successfully!")

if __name__ == '__main__':
    # Start the client once when app starts
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(initialize_client())
    
    # Get port from environment variable (Railway provides this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
