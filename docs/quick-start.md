---
site_name: Mesh - Documentation
site_author: Arnav Das
site_url: https://arnavdas88.github.io/mesh/
site_description: Mesh is a leaderless, weakly coupled, distributed data store python library designed for FastAPI applications. It enables multiple independent service instances to form a peer-to-peer network and maintain a shared, eventually consistent state store.
repo_name: mesh
author: Arnav Das
repo_url: https://github.com/arnavdas88/mesh/
hide:
  - navigation
---

# Run a Two-Node Mesh Cluster in Minutes

Connect two FastAPI nodes and synchronize shared state with Mesh in under five minutes. Install, create nodes, join a cluster, and read shared data.

This guide walks you through installing Mesh, wiring it into two FastAPI applications, joining them into a peer-to-peer cluster, and verifying that state syncs correctly across both nodes. By the end you will have a working two-node Mesh cluster running on your local machine.

## Install Mesh
Mesh is not yet published to PyPI. Install it directly from the GitHub repository:

```bash
$ pip install git+https://github.com/arnavdas88/mesh.git
```

Alternatively, clone the repository and install in editable mode — useful if you want to inspect or modify the source alongside your own application code:

```bash
$ git clone https://github.com/arnavdas88/mesh.git
$ cd mesh
$ pip install -e .
```

## Create your first node

Create a file called `node_a.py`. Import FastAPI and Node, instantiate both, and expose a simple endpoint that returns the node’s current shared state:

```py
from fastapi import FastAPI, Body
from mesh.node import Node

app = FastAPI()
node = Node(name="node-a", app=app, action_on_conflict="merge")

@app.get("/")
async def root():
    return node.data.to_dict()

@app.post("/push-data")
async def push(payload: dict = Body(...)):
    await node.put_data(payload)
    return node.data.to_dict()
```

Passing your app instance to Node is all it takes to register the `/mesh` WebSocket endpoint. Mesh handles the rest automatically.

## Start a second node and join the cluster
Create a file called `node_b.py`. Use a lifespan context manager to join `node-a` during startup, sync state, and deregister cleanly on shutdown:

```py
import asyncio
import contextlib

from fastapi import FastAPI
from mesh.node import Node

SLEEP = 1

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: wait briefly, then join node-a and sync
    await asyncio.sleep(SLEEP)
    await node.join(["ws://localhost:8000/mesh"])
    await asyncio.sleep(SLEEP)

    await node.sync_up()
    await asyncio.sleep(SLEEP)

    # Register this node in the shared state
    await node.put_data({"__node_b__": {"name": "node-b", "status": "up"}})

    yield

    # Shutdown: remove self from shared state and propagate
    await node.pop_data("__node_b__")
    await node.sync_up()
    await asyncio.sleep(SLEEP)


app = FastAPI(lifespan=lifespan)
node = Node(name="node-b", app=app, action_on_conflict="merge")

@app.get("/")
async def root():
    return node.data.to_dict()
```

Start `node-a` on port 8000 first, then start `node-b` on port 8001. The lifespan hook fires automatically when uvicorn brings the application up.

```bash
# Terminal 1
$ uvicorn node_a:app --port 8000
```

```bash
# Terminal 2
$ uvicorn node_b:app --port 8001
```

## Verify sync
After `sync_up()` completes, both nodes hold an identical snapshot of the shared `MonotonicDict`. Send a `GET /` request to each node and confirm the responses match:

```bash
curl http://localhost:8000/
# {"__node_b__": {"name": "node-b", "status": "up"}}

curl http://localhost:8001/
# {"__node_b__": {"name": "node-b", "status": "up"}}
```

Any write made through `put_data()` on either node propagates to the other automatically. You do not need to poll or manually trigger additional syncs. Mesh pushes state changes to all connected peers as they happen.