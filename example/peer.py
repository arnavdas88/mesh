from contextlib import asynccontextmanager
import sys
sys.path.append(".")

import asyncio
from fastapi import FastAPI
from mesh.node import Node
import uvicorn

NAME = "Bob"



@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup

    await node.join(["ws://localhost:8000/mesh"])

    await node.sync_up()
    await asyncio.sleep(2)

    node_lists = await node.get_data("__node_lists__", default = [])
    await node.put_data({"__node_lists__": node_lists + [NAME]})
    node_lists = await node.get_data("__node_lists__", default = [])
    print(f"{node_lists=}")

    yield
    # shutdown (optional)



app = FastAPI(lifespan=lifespan)
node = Node(name=NAME, app=app)


@app.get("/")
async def root():
    node_lists = await node.get_data("__node_lists__", default = [])
    if NAME not in node_lists:
        await node.put_data({"__node_lists__": node_lists + [NAME]})
        node_lists = await node.get_data("__node_lists__", default = [])

    return {"name": NAME, "status": "running", "data": node_lists}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

