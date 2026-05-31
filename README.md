# Mesh - for FastAPI

## Use
```py
import socket
import asyncio
import contextlib

from fastapi import FastAPI
from mesh.node import Node

NAME = socket.gethostname()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Put some data during startup
    await node.put_data({f"__node_{NAME.lower()}__": {"name": NAME, ...}})

    yield

    # Shutdown
    # Remove the data during shutdown
    await node.pop_data(f"__node_{NAME}__")
    await node.sync_up()
    await asyncio.sleep(SLEEP)


app = FastAPI(title=f"Test Server {NAME}", lifespan=lifespan)
node = Node(name=NAME, app=app, action_on_conflict="merge")


@app.get("/")
async def root():
    internal_data = node.data.to_dict()
    return {"name": NAME, "status": "running", "internal_data": internal_data}


@app.get("/join")
async def join(url: str):
    await node.join([url])
    await node.sync_up()
    await asyncio.sleep(SLEEP)

    internal_data = node.data.to_dict()
    return {"name": NAME, "status": "running", "internal_data": internal_data}
```

## Local Dev Installation
```bash
$ /usr/bin/env /usr/bin/python3 -m pip install --break-system-packages -e .
```


# Example
```bash
$ docker compose up
```