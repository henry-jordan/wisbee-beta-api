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
import ast

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
            message = {
                'id': message_id,
                'message': text,
            }

            await manager.send_message(json.dumps(message), websocket)
        except Exception as e:
            message = {
                'id': message_id,
                'message': '',
                'special': 'failed',
            }
            await manager.send_message(json.dumps(message), websocket)

            return
    message = {
        'id': message_id,
        'message': '',
        'special': 'complete',
    }
    
    await manager.send_message(json.dumps(message), websocket)

@app.get('/')
async def root():
    return {"message": "Hello World 🤩"}

@app.get('/status')
async def status():
    return {"message": "👍"}

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = time()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        else:
            print("WebSocket not found in active connections")

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def close_inactive_connections(self, inactive_timeout):
        while True:
            await asyncio.sleep(inactive_timeout)
            now = time()
            connections_to_close = [
                websocket for websocket, last_activity_time in self.active_connections.items()
                if now - last_activity_time > inactive_timeout
            ]
            for websocket in connections_to_close:
                message = {
                    'id': '',
                    'message': '',
                    'special': 'timeout',
                }

                await self.send_message(json.dumps(message), websocket)
                await self.close_connection(websocket)

    async def close_connection(self, websocket: WebSocket):
        print('closing connection')

        await websocket.close()
        self.disconnect(websocket)


manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(manager.close_inactive_connections(inactive_timeout=900))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            message_id = int(time() * random())
            messages = ast.literal_eval(data)

            manager.active_connections[websocket] = time()

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