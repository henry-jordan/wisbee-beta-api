from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import uvicorn
from dotenv import load_dotenv
from time import time
from random import random
import json
import asyncio
from openai import AsyncOpenAI
import os

load_dotenv()

app = FastAPI()
handler = Mangum(app)
llm = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

origins = [
    'http://localhost',
    'http://localhost:5000'
    'http://localhost:5000/websocketDebug'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def llm_default_response(messages):
    try:
        result = await llm.chat.completions.create(
            model = 'gpt-3.5-turbo-1106',
            messages=messages,
            stream=True,
        )
        return result
    except:
        return None

async def stream_llm_response(messages, message_id, websocket):
    response = await llm_default_response(messages)

    async for line in response:
        text = line.choices[0].delta.content
        try:
            if len(text):
                message = {
                    'id': message_id,
                    'message': text,
                }

                await manager.send_message(json.dumps(message), websocket)
        except Exception as e:
            message = {
                'id': message_id,
                'message': e,
                'special': 'Failed',
            }

@app.get('/')
async def root():
    return {"message": "Hello World 🤩"}

@app.get('/status')
async def status():
    return {"message": "👍"}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)


manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            message_id = int(time() * random())
            messages = [
                {'role': 'user', 'content': data}
            ]

            asyncio.create_task(stream_llm_response(messages, message_id, websocket))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def send_delayed_messages(message_id, websocket):
    data = [' Hello', ' World!', ' This', ' message', ' is', ' being', ' delayed.']

    for chunk in data:
        message = {
            'id': message_id,
            'message': chunk,
        }

        await manager.send_message(json.dumps(message), websocket)
        await asyncio.sleep(0.75)