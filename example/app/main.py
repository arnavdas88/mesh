import os, sys
import socket
import asyncio
import platform
import contextlib
import logging

from fastapi import FastAPI
from mesh.node import Node

from .utils import get_internal_data

NAME = socket.gethostname()
UNAME = platform.uname()
HOSTNAME = socket.gethostname()
CONFIG = { 
    "hostname": HOSTNAME, "cwd": os.getcwd(), 
    "host": socket.gethostbyname(HOSTNAME), 
    "python": sys.version,
    "platform": {
        "Operating System": UNAME.system,
        "OS Release": UNAME.release,
        "OS Version": UNAME.version,
        "Architecture": UNAME.machine,
        "Processor Name": UNAME.processor,
    }
}
SLEEP = 1
URLS_TO_JOIN = os.getenv("JOIN_TO") or None


logging.basicConfig(
    level=logging.INFO,
    format='\t%(levelname)s   %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger  = logging.getLogger()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # startup

    # Join partition peers (if any)
    if URLS_TO_JOIN:
        await asyncio.sleep(SLEEP)
        await node.join(URLS_TO_JOIN.split(","))
        await asyncio.sleep(SLEEP)
 
    await node.sync_up()
    await asyncio.sleep(SLEEP)

    # Register self
    await node.put_data({f"__node_{NAME.lower()}__": {"name": NAME, "config": CONFIG}})

    yield
    # shutdown (optional)

    await node.pop_data(f"__node_{NAME}__")
    await node.sync_up()
    await asyncio.sleep(SLEEP)


app = FastAPI(title=f"Test Server {NAME}", lifespan=lifespan)
node = Node(name=NAME, app=app, action_on_conflict="merge")

def callback(data, key, value, operation, source: Node):
    logger.info( " ".join(
            [
                f"Got operation \"{operation}\"",
                f"from {source} for key \"{key}\"" if source else f"for key \"{key}\"",
            ]
        )
    )

node.data.register_global_callback(callback)

@app.get("/")
async def root():
    internal_data = get_internal_data(node.data)
    return {"name": NAME, "status": "running", "internal_data": internal_data}

@app.get("/join")
async def join(url: str):
    await node.join([url])
    await node.sync_up()
    await asyncio.sleep(SLEEP)

    internal_data = get_internal_data(node.data)
    return {"name": NAME, "status": "running", "internal_data": internal_data}

