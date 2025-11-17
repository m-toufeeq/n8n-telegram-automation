

api_id = 39955957
api_hash = "03ecd7b069da3c4da117f1d21ac14f54"
SESSION_NAME = "my_user_session"

from telethon import TelegramClient
import asyncio


phone = "+923368554422"  # your phone number with country code

async def main():
    client = TelegramClient('session_name', api_id, api_hash)
    await client.start(phone=phone)

    group = "https://t.me/+obmFfJdYLWIwYjk0"   # or group username
    message = "This is an automated message."

    await client.send_message(group, message)
    print("Message sent successfully!")
    await client.disconnect()

asyncio.run(main())
