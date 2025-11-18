from flask import Flask, request, jsonify
from telethon import TelegramClient
import asyncio
import os
from threading import Thread

app = Flask(__name__)

# Your credentials
api_id = 39955957
api_hash = "03ecd7b069da3c4da117f1d21ac14f54"
phone = "+923368554422"

# Use file-based session
client = TelegramClient('session_name', api_id, api_hash)

# Global event loop for async operations
loop = None

def start_async_loop():
    """Start asyncio loop in a separate thread"""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def initialize_client():
    """Initialize the Telegram client - assumes session file exists"""
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("ERROR: Session file not found or invalid!")
            print("Please create session file locally first and upload to Railway")
            return False
        print("Telegram client connected successfully!")
        return True
    except Exception as e:
        print(f"Error connecting client: {e}")
        return False

async def send_telegram_message(group, message):
    """Send message to Telegram group"""
    if not client.is_connected():
        await client.connect()
    
    await client.send_message(group, message)
    return True

@app.route('/send-message', methods=['POST'])
def send_message():
    """Endpoint to send Telegram messages - called by n8n"""
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
        future.result()
        
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

# Start async loop in background thread immediately when module loads
thread = Thread(target=start_async_loop, daemon=True)
thread.start()

# Wait for loop to start
import time
time.sleep(0.5)

# Initialize client
future = asyncio.run_coroutine_threadsafe(initialize_client(), loop)
future.result()

if __name__ == '__main__':
    # Get port from environment variable (Railway provides this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
