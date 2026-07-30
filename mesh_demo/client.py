import socket
import random
import uvicorn
import asyncio
import contextlib

from fastapi import FastAPI, Body
from meshd.node import Node
from meshd.monotonic_dict import Op

NAME = socket.gethostname()
RANDOM_SUFFIX = random.randint(1000, 9999)
SLUG_NAME = f"{NAME.lower().replace('.', '_')}_{RANDOM_SUFFIX}"  # Replace dots with underscores for valid identifiers
JOIN_URLS = [ "wss://mesh-demo.fastapicloud.dev/mesh" ]

SLEEP = 1

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: wait briefly, then join node-a and sync
    await node.sync_up()
    await asyncio.sleep(SLEEP)
    await node.join(JOIN_URLS)
    await asyncio.sleep(SLEEP)

    await node.sync_up()
    await asyncio.sleep(SLEEP)

    # Register this node in the shared state
    await node.put_data({f"__node_{SLUG_NAME}__": {"name": NAME, "slug": SLUG_NAME, "status": "up"}})

    yield

    # Shutdown: remove self from shared state and propagate
    await node.pop_data(f"__node_{SLUG_NAME}__")
    await asyncio.sleep(SLEEP)
    await node.sync_up()

app = FastAPI(title=f"Test Server {NAME}", lifespan=lifespan)
node = Node(name=NAME, app=app, action_on_conflict="error") 

@app.get("/")
async def root():
    internal_data = node.data.to_dict() 
    return {"message": "Hello World", "name": NAME, "slug": SLUG_NAME, "status": "running", "internal_data": internal_data}

@app.get("/join")
async def join(url: str):
    await node.join([url]) 
    await node.sync_up()
    await asyncio.sleep(2)  # Wait some time for the data to synchronize

    internal_data = node.data.to_dict()
    return {"name": NAME, "slug": SLUG_NAME, "status": "running", "internal_data": internal_data}

@app.post("/push-data")
async def push(payload: dict = Body(...)):
    await node.put_data(payload)
    await asyncio.sleep(2) # Wait some time for the data to propagate

    internal_data = node.data.to_dict()
    return {"name": NAME, "slug": SLUG_NAME, "status": "running", "internal_data": internal_data}

if __name__ == "__main__":
    # "main:app" string means -> Look in main.py for the object named app
    uvicorn.run(app, host="localhost", port=8001)