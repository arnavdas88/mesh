import socket
import asyncio

from fastapi import FastAPI, Body
from meshd.node import Node

# NAME = socket.gethostname()
NAME = "node1"  # You can change this to a unique name for each node

def callback(node, key, value, operation, src_node):
    print(f"Callback triggered for key: {key}, value: {value}, operation: {operation}, src_node: {src_node}")

app = FastAPI(title=f"Test Server {NAME}", )
# node = Node(name=NAME, app=app, action_on_conflict="merge", ) 
node = Node(name=NAME, app=app, action_on_conflict="error", ) 
node.data.register_global_callback(callback)


@app.get("/")
async def root():
    internal_data = node.data.to_dict() 
    return {"message": "Hello World", "name": NAME, "status": "running", "internal_data": internal_data}


@app.get("/join")
async def join(url: str):
    await node.join([url]) 
    await node.sync_up()
    await asyncio.sleep(2)  # Wait some time for the data to synchronize

    internal_data = node.data.to_dict()
    return {"name": NAME, "status": "running", "internal_data": internal_data}

@app.post("/push-data")
async def push(payload: dict = Body(...)):
    await node.put_data(payload)
    await asyncio.sleep(2) # Wait some time for the data to propagate

    internal_data = node.data.to_dict()
    return {"name": NAME, "status": "running", "internal_data": internal_data}