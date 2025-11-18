from flask import Flask, request, jsonify
from telethon import TelegramClient, functions
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

async def join_telegram_group(invite_link):
    """Join a Telegram group using invite link"""
    if not client.is_connected():
        await client.connect()
    
    try:
        # Extract the hash from the invite link
        # Handles formats like:
        # https://t.me/+inviteHash
        # https://t.me/joinchat/inviteHash
        # t.me/+inviteHash
        
        if '+' in invite_link:
            invite_hash = invite_link.split('+')[-1]
        elif 'joinchat/' in invite_link:
            invite_hash = invite_link.split('joinchat/')[-1]
        else:
            raise ValueError("Invalid invite link format")
        
        # Join the group
        updates = await client(functions.messages.ImportChatInviteRequest(invite_hash))
        
        # Get the group info
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
        
        # Handle common errors
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

@app.route('/', methods=['GET'])
def home():
    """Root endpoint"""
    return jsonify({
        'status': 'running',
        'endpoints': {
            '/health': 'GET - Health check',
            '/send-message': 'POST - Send telegram message',
            '/join-group': 'POST - Join a telegram group'
        }
    }), 200

@app.route('/join-group', methods=['POST'])
def join_group():
    """Endpoint to join Telegram groups - called by n8n"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        invite_link = data.get('invite_link')
        
        if not invite_link:
            return jsonify({
                'status': 'error',
                'message': 'invite_link field is required'
            }), 400
        
        # Run async function in the same loop
        future = asyncio.run_coroutine_threadsafe(
            join_telegram_group(invite_link), 
            loop
        )
        result = future.result()
        
        return jsonify({
            'status': 'success',
            'message': 'Joined group successfully!',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/send-message', methods=['GET', 'POST'])
def send_message():
    """Endpoint to send Telegram messages - called by n8n"""
    
    # Handle GET for debugging
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
