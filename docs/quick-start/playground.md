---
title: Playground
description: Play around with meshd

repo_name: meshd
author: Arnav Das
repo_url: https://github.com/arnavdas88/meshd/

meta:
  - name: keywords
    content: mesh, meshd, fastapi, mkdocs, distributed system, leaderless, cloud native, quick start
  - name: robots
    content: index, follow
---

A [playground](https://mesh-demo.fastapicloud.dev) exists at `mesh-demo.fastapicloud.dev` to get a feel of meshd, hosted through [FastAPI Cloud](fastapicloud.com). 

The OpenAPI Swagger Docs of the playground can be found at [mesh-demo.fastapicloud.dev/docs](https://mesh-demo.fastapicloud.dev/docs).

??? note "Surfing on the demo"

    The playground hosts its index at [mesh-demo.fastapicloud.dev](https://mesh-demo.fastapicloud.dev/). A 
    curl command returns the content served at that endpoint.

    ```{.bash .no-copy .select}
    $ curl -X 'GET' 'https://mesh-demo.fastapicloud.dev/' -H 'accept: application/json' | jq

    {
      "message": "Hello World",
      "name": "node1",
      "status": "running",
      "internal_data": {}
    }
    ```
    
    Following this, all meshd application hosts a `meshd-info` endpoint, serving important information regarding
    the versioning, docs, join,  configuration, etc. For the playground, the endpoint exists at [mesh-demo.fastapicloud.dev/meshd-info](https://mesh-demo.fastapicloud.dev/meshd-info)

    ```{.bash .no-copy .select}
    $ curl -X 'GET' 'https://mesh-demo.fastapicloud.dev/meshd-info' -H 'accept: application/json' | jq

    {
      "name": "node1",
      "servers": [],
      "version": "2026.0.2",  # (1)!
      "action_on_conflict": "error",  # (2)!
      "domain": "mesh-demo.fastapicloud.dev", # (3)!
      "docs_url": "https://mesh-demo.fastapicloud.dev/docs", # (4)!
      "join_url": "wss://mesh-demo.fastapicloud.dev/meshd" # (5)!
    }
    ```

    1. Shows the version of the `meshd` package in that node.
    2. Shows the operating mode of conflict resolution. The available modes of conflict resolution are `accept`, `merge`, `error`, `warn`, `exception`, `ignore`.
    3. Shows the host of the query. This can be used to detect the hostname through which, the node is accessible from a network.
    4. Shows the Swagger OpenAPI documentation url of the playground.
    5. Shows the URL of the playground to which, other nodes can connect to, in order to join the cluster.

Any server (`local` or `remote`) can connect and be a part of the cluster by connecting to the `join_url` using the `node.join([join_url])` function.

```py
import uvicorn, asyncio

from fastapi import FastAPI, Body
from meshd.node import Node

NAME = ...

async def lifespan(app: FastAPI):
    # Startup: wait briefly, then join node-a and sync
    await node.sync_up()
    await asyncio.sleep(1)
    await node.join([join_url])
    await node.sync_up()
    await asyncio.sleep(1)

    # Register this node in the shared state
    await node.put_data({f"__node_{NAME}__": {"name": NAME, "status": "up"}})

    yield

    # Shutdown: remove self from shared state and propagate
    await node.pop_data(f"__node_{NAME}__")
    await asyncio.sleep(1)
    await node.sync_up()

app = FastAPI(title=f"Test Server {NAME}", lifespan=lifespan)
node = Node(name=NAME, app=app, action_on_conflict="merge") 

join_url = "wss://mesh-demo.fastapicloud.dev/meshd" # (1)!

@app.get("/")
async def root():
    internal_data = node.data.to_dict() 
    return {"name": NAME, "status": "running", "internal_data": internal_data}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)
```

1. This is the joining url of the playground node. Connecting to this url, will make your code, join the playgrounds cluster. You can find the url at [mesh-demo.fastapicloud.dev/meshd-info](https://mesh-demo.fastapicloud.dev/meshd-info)