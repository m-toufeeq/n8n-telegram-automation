from flask import Flask, request, jsonify
from telethon import TelegramClient, functions
from telethon.tl.functions.channels import LeaveChannelRequest 
import asyncio
import os
from threading import Thread
from datetime import datetime, timedelta, timezone 

app = Flask(__name__)

# Your credentials
api_id = 39955957
api_hash = "03ecd7b069da3c4da117f1d21ac14f54"
phone = "+923368554422"

# Use file-based session
client = TelegramClient('session_name', api_id, api_hash)

loop = None

def start_async_loop():
    """Start asyncio loop in a separate thread"""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def initialize_client():
    """Initialize the Telegram client and leave the crash-causing channel"""
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("ERROR: Session file not found or invalid!")
            return False
        
        # --- CRITICAL FIX: FORCE LEAVE THE SPAM CHANNEL ---
        try:
            # This is the ID of the "$MARIO" spam channel from your logs
            spam_channel_id = 2376693784 
            print(f"Attempting to leave spam channel {spam_channel_id}...")
            await client(LeaveChannelRequest(spam_channel_id))
            print("SUCCESS: Left the spam channel! The crash should stop now.")
        except Exception as e:
            # If you already left it, this is fine.
            print(f"Note: Could not leave channel (might already be left): {e}")
        # --------------------------------------------------

        print("Telegram client connected successfully!")
        return True
    except Exception as e:
        print(f"Error connecting client: {e}")
        return False

# --- ASYNC TELEGRAM FUNCTIONS ---

async def send_telegram_message(group, message):
    if not client.is_connected():
        await client.connect()
    await client.send_message(group, message)
    return True

async def reply_to_telegram_message(group_entity, message_id, reply_text):
    if not client.is_connected():
        await client.connect()
    
    # Fetch the specific message to reply to
    message = await client.get_messages(group_entity, ids=message_id)
    if message:
        await message.reply(reply_text)
        return True
    return False

async def fetch_new_messages_for_ai(group, lookback_seconds=60):
    if not client.is_connected():
        await client.connect()

    entity = await client.get_entity(group)
    time_threshold = datetime.now(timezone.utc) - timedelta(seconds=lookback_seconds)
    messages_to_process = []
    
    # Wrapped in try/except to prevent crashing on individual bad messages
    try:
        async for message in client.iter_messages(entity, limit=50):
            try:
                # Stop if message is older than threshold
                if message.date < time_threshold:
                    break
                
                # Only process text messages that are NOT sent by us
                if message.text and not message.out and not message.action:
                    messages_to_process.append({
                        'message_id': message.id,
                        'sender_id': message.sender_id,
                        'group_id': entity.id,
                        'group_username': entity.username if hasattr(entity, 'username') else str(entity.id),
                        'text': message.text, 
                        'date_utc': message.date.isoformat()
                    })
            except Exception as e:
                print(f"Skipping a bad message: {e}")
                continue
    except Exception as e:
        print(f"Error iterating messages: {e}")

    return list(reversed(messages_to_process))

# --- FLASK ROUTES ---

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'running',
        'endpoints': {
            '/fetch-messages': 'POST - Get new messages',
            '/reply-to': 'POST - Reply to a message'
        }
    }), 200

@app.route('/fetch-messages', methods=['POST'])
def fetch_messages():
    try:
        data = request.get_json()
        if not data or 'group' not in data:
            return jsonify({'status': 'error', 'message': 'group field is required'}), 400

        group = data.get('group')
        lookback = data.get('lookback', 60) 
        
        future = asyncio.run_coroutine_threadsafe(
            fetch_new_messages_for_ai(group, lookback), 
            loop
        )
        messages = future.result()
        
        return jsonify({
            'status': 'success',
            'messages': messages
        }), 200
    except Exception as e:
        # This will catch the crash if it still happens and show it in n8n
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/reply-to', methods=['POST'])
def reply_to():
    try:
        data = request.get_json()
        group = data.get('group')
        message_id = data.get('message_id')
        reply_text = data.get('reply_text')
        
        future = asyncio.run_coroutine_threadsafe(
            reply_to_telegram_message(group, message_id, reply_text), 
            loop
        )
        success = future.result()
        
        return jsonify({'status': 'success' if success else 'error'}), 200 if success else 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

# Start background components
thread = Thread(target=start_async_loop, daemon=True)
thread.start()

import time
time.sleep(0.5)

future = asyncio.run_coroutine_threadsafe(initialize_client(), loop)
future.result()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
