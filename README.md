# Mesh - A Distributed Data Structure
<p align="center">
    <img src="https://github.com/arnavdas88/mesh/blob/main/docs/assets/illustration-1.png">
</p>
<p align="center">
    Mesh - Distributed Data Structure for FastAPI Servers
</p>

---


## Usage
```py
from mesh.node import Node

app = FastAPI()
node = Node(
    name=NAME, # Assign a name to this server
    app=app,   # The Fastapi application to hook into
    action_on_conflict="merge" # Default action for conflict management
)

...

# To join to a cluster
await node.join([url])   # Add the joining url
await node.sync_up()     # Sync up the data
await asyncio.sleep(...) # Wait a few seconds for the sync up to finish

...

# Fetch current data
internal_data = node.data.to_dict()

```


## Example Code
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


# Example Simulation
```bash
$ docker compose up
```
