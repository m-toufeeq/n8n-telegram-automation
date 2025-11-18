from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import os
from threading import Thread

app = Flask(__name__)

# Your credentials
api_id = 39955957
api_hash = "03ecd7b069da3c4da117f1d21ac14f54"
phone = "+923368554422"

# Use StringSession from environment variable or empty string for local
session_string = os.environ.get('TELEGRAM_SESSION', '')
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# Global event loop for async operations
loop = None

def start_async_loop():
    """Start asyncio loop in a separate thread"""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def initialize_client():
    """Initialize and authenticate the Telegram client"""
    try:
        await client.start(phone=phone)
        print("Telegram client authenticated successfully!")
    except Exception as e:
        print(f"Error initializing client: {e}")
        # If session is corrupted, disconnect and try to reconnect
        await client.disconnect()
        # Delete the session file if it exists
        import os
        if os.path.exists('session_name.session'):
            os.remove('session_name.session')
            print("Deleted corrupted session file")
        # Try to start again
        await client.start(phone=phone)
        print("Telegram client authenticated successfully after reset!")

async def send_telegram_message(group, message):
    """Send message to Telegram group"""
    await client.send_message(group, message)
    return True

@app.route('/send-message', methods=['POST'])
def send_message():
    """Endpoint to send Telegram messages"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        group = data.get('group')
        message = data.get('message')
        
        if not group:
            return jsonify({
                'status': 'error',
                'message': 'group field is required'
            }), 400
        
        if not message:
            return jsonify({
                'status': 'error',
                'message': 'message field is required'
            }), 400
        
        # Run async function in the same loop
        future = asyncio.run_coroutine_threadsafe(
            send_telegram_message(group, message), 
            loop
        )
        future.result()  # Wait for completion
        
        return jsonify({
            'status': 'success',
            'message': 'Message sent successfully!',
            'sent_to': group
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

if __name__ == '__main__':
    # Start async loop in background thread
    thread = Thread(target=start_async_loop, daemon=True)
    thread.start()
    
    # Wait a moment for loop to start
    import time
    time.sleep(0.5)
    
    # Initialize client
    future = asyncio.run_coroutine_threadsafe(initialize_client(), loop)
    future.result()
    
    # Get port from environment variable (Railway provides this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
