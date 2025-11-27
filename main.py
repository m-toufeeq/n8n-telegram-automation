from flask import Flask, request, jsonify
from telethon import TelegramClient, functions
import asyncio
import os
from threading import Thread
# New imports for time filtering
from datetime import datetime, timedelta, timezone 

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

# --- ASYNC TELEGRAM FUNCTIONS ---

async def send_telegram_message(group, message):
    """Send message to Telegram group"""
    if not client.is_connected():
        await client.connect()
    
    await client.send_message(group, message)
    return True

async def reply_to_telegram_message(group_entity, message_id, reply_text):
    """Reply to a specific message ID in a group."""
    if not client.is_connected():
        await client.connect()

    # Get the message object by ID
    message = await client.get_messages(group_entity, ids=message_id)

    if message:
        await message.reply(reply_text)
        return True
    return False

async def fetch_new_messages_for_ai(group, lookback_seconds=60):
    """
    Fetch new, non-outgoing messages from a group to be processed by an AI.
    Returns a list of structured message data.
    """
    if not client.is_connected():
        await client.connect()

    # Get the group entity
    entity = await client.get_entity(group)

    # Calculate the time threshold (UTC) - Default to 60 seconds lookback
    time_threshold = datetime.now(timezone.utc) - timedelta(seconds=lookback_seconds)

    messages_to_process = []
    
    # Fetch messages (limit to 50 for safety and performance)
    async for message in client.iter_messages(entity, limit=50):
        # Stop if message is older than threshold
        if message.date < time_threshold:
            break
        
        # Only process text messages that are NOT sent by us.
        if message.text and not message.out and not message.action:
            messages_to_process.append({
                'message_id': message.id,
                'sender_id': message.sender_id,
                'group_id': entity.id,
                'group_username': entity.username if hasattr(entity, 'username') else str(entity.id),
                'text': message.text, # This is the content you pass to your AI agent
                'date_utc': message.date.isoformat()
            })

    # Return messages in oldest-to-newest order for conversational flow
    return list(reversed(messages_to_process))


async def join_telegram_group(invite_link):
    """Join a Telegram group using invite link (Kept for compatibility)"""
    if not client.is_connected():
        await client.connect()
    
    try:
        # Logic for joining group... (omitted for brevity, keep the original code)
        if '+' in invite_link:
            invite_hash = invite_link.split('+')[-1]
        elif 'joinchat/' in invite_link:
            invite_hash = invite_link.split('joinchat/')[-1]
        else:
            raise ValueError("Invalid invite link format")
        
        updates = await client(functions.messages.ImportChatInviteRequest(invite_hash))
        
        if hasattr(updates, 'chats') and len(updates.chats) > 0:
            chat = updates.chats[0]
            return {
                'success': True,
                'group_title': chat.title,
                'group_id': chat.id
            }
        
        return {'success': True, 'message': 'Joined successfully'}
        
    except Exception as e:
        error_message = str(e)
        
        if 'INVITE_HASH_EXPIRED' in error_message:
            raise Exception("Invite link has expired")
        elif 'USER_ALREADY_PARTICIPANT' in error_message:
            return {'success': True, 'message': 'Already a member of this group'}
        elif 'CHANNELS_TOO_MUCH' in error_message:
            raise Exception("You have joined too many channels/groups. Leave some first.")
        elif 'INVITE_HASH_INVALID' in error_message:
            raise Exception("Invalid invite link")
        else:
            raise Exception(f"Failed to join group: {error_message}")

# --- FLASK ROUTES ---

@app.route('/', methods=['GET'])
def home():
    """Root endpoint (Updated to show new routes)"""
    return jsonify({
        'status': 'running',
        'endpoints': {
            '/health': 'GET - Health check',
            '/send-message': 'POST - Send telegram message',
            '/join-group': 'POST - Join a telegram group',
            '/fetch-messages': 'POST - Get new messages for AI processing',
            '/reply-to': 'POST - Send AI-generated reply to a specific message ID',
        }
    }), 200

# Endpoint to join Telegram groups (Kept for compatibility)
@app.route('/join-group', methods=['POST'])
def join_group():
    """Endpoint to join Telegram groups - called by n8n"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'Request body is required'}), 400
        
        invite_link = data.get('invite_link')
        
        if not invite_link:
            return jsonify({'status': 'error', 'message': 'invite_link field is required'}), 400
        
        future = asyncio.run_coroutine_threadsafe(join_telegram_group(invite_link), loop)
        result = future.result()
        
        return jsonify({
            'status': 'success',
            'message': 'Joined group successfully!',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Endpoint to send Telegram messages (Kept for compatibility)
@app.route('/send-message', methods=['GET', 'POST'])
def send_message():
    """Endpoint to send Telegram messages - called by n8n"""
    
    if request.method == 'GET':
        return jsonify({
            'status': 'info',
            'message': 'This endpoint accepts POST requests with JSON body',
            'required_fields': ['group', 'message'],
            'example': {
                'group': 'https://t.me/+yourGroupLink',
                'message': 'Your message here'
            }
        }), 200
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'Request body is required'}), 400
        
        group = data.get('group')
        message = data.get('message')
        
        if not group:
            return jsonify({'status': 'error', 'message': 'group field is required'}), 400
        
        if not message:
            return jsonify({'status': 'error', 'message': 'message field is required'}), 400
        
        future = asyncio.run_coroutine_threadsafe(send_telegram_message(group, message), loop)
        future.result()
        
        return jsonify({
            'status': 'success',
            'message': 'Message sent successfully!',
            'sent_to': group
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# --- NEW ENDPOINTS FOR AI AUTOMATION ---

@app.route('/fetch-messages', methods=['POST'])
def fetch_messages():
    """Endpoint to fetch new messages for AI processing - Step 1 of the new workflow."""
    try:
        data = request.get_json()
        
        if not data or 'group' not in data:
            return jsonify({'status': 'error', 'message': 'group field is required in the body.'}), 400

        group = data.get('group')
        # lookback determines how far back in time to check for messages (in seconds)
        lookback = data.get('lookback', 60) 
        
        # Run async function to fetch messages
        future = asyncio.run_coroutine_threadsafe(
            fetch_new_messages_for_ai(group, lookback), 
            loop
        )
        messages = future.result()
        
        return jsonify({
            'status': 'success',
            'message': f'Fetched {len(messages)} new messages for AI processing.',
            'messages': messages
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/reply-to', methods=['POST'])
def reply_to():
    """Endpoint to send AI-generated reply - Step 2 of the new workflow."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['group', 'message_id', 'reply_text']
        if not data or not all(field in data for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': f'Request body requires all fields: {", ".join(required_fields)}'
            }), 400
        
        group = data.get('group')
        message_id = data.get('message_id')
        reply_text = data.get('reply_text')
        
        # Run async function to reply to the specific message ID
        future = asyncio.run_coroutine_threadsafe(
            reply_to_telegram_message(group, message_id, reply_text), 
            loop
        )
        success = future.result()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Successfully replied to message ID {message_id} in group {group}'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to find or reply to message ID {message_id} in group {group}'
            }), 500
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
