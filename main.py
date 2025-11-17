from fastapi import FastAPI
from pydantic import BaseModel
from telethon import TelegramClient
import uvicorn
import asyncio

api_id = 39955957
api_hash = "03ecd7b069da3c4da117f1d21ac14f54"
SESSION_NAME = "my_user_session"

app = FastAPI()

class MessagePayload(BaseModel):
    group: str
    message: str

@app.post("/send")
async def send_message(payload: MessagePayload):
    client = TelegramClient(SESSION_NAME, api_id, api_hash)
    await client.start()

    try:
        await client.send_message(payload.group, payload.message)
        return {"status": "success", "sent_to": payload.group}
    except Exception as e:
        return {"status": "error", "details": str(e)}
    finally:
        await client.disconnect()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
