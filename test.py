import websockets
import asyncio
import json

async def listen_progress(batch_id):
    url = f"ws://localhost:8000/ws/progress/{batch_id}"
    async with websockets.connect(url) as ws:
        async for msg in ws:
            print("Progress:", json.loads(msg))

asyncio.run(listen_progress("ed5f92a7-d1a8-4262-8b2e-1bb910ee50e3"))