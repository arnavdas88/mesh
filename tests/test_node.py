import asyncio
import pytest
import uvicorn
import httpx

from fastapi import FastAPI
from contextlib import asynccontextmanager

from mesh.node import Node


# -----------------------------
# Utilities
# -----------------------------

class UvicornTestServer:
    """
    Runs a uvicorn server in background task for testing.
    """

    def __init__(self, app, host="127.0.0.1", port=0):
        self.config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="error",
            lifespan="on",
        )
        self.server = uvicorn.Server(self.config)
        self.task = None

    async def start(self):
        self.task = asyncio.create_task(self.server.serve())
        while not self.server.started:
            await asyncio.sleep(0.05)

    async def stop(self):
        self.server.should_exit = True
        await self.task


# -----------------------------
# Fixtures
# -----------------------------

@pytest.fixture
async def alice_server():
    NAME = "Alice"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await node.sync_up()
        await asyncio.sleep(1)

        node_lists = await node.get_data("__node_lists__", default=[])
        await node.put_data({"__node_lists__": node_lists + [NAME]})

        yield

    app = FastAPI(lifespan=lifespan)
    node = Node(name=NAME, app=app)

    @app.get("/")
    async def root():
        node_lists = await node.get_data("__node_lists__", default=[])
        return {"name": NAME, "data": node_lists}

    server = UvicornTestServer(app, port=8000)
    await server.start()

    yield node

    await server.stop()


@pytest.fixture
async def bob_server():
    NAME = "Bob"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await node.join(["ws://127.0.0.1:8000/mesh"])
        await asyncio.sleep(1)

        await node.sync_up()
        await asyncio.sleep(1)

        node_lists = await node.get_data("__node_lists__", default=[])
        await node.put_data({"__node_lists__": node_lists + [NAME]})

        yield

    app = FastAPI(lifespan=lifespan)
    node = Node(name=NAME, app=app)

    @app.get("/")
    async def root():
        node_lists = await node.get_data("__node_lists__", default=[])
        return {"name": NAME, "data": node_lists}

    server = UvicornTestServer(app, port=8001)
    await server.start()

    yield node

    await server.stop()


# -----------------------------
# Tests
# -----------------------------

@pytest.mark.asyncio
async def test_nodes_connect_and_sync(alice_server, bob_server):
    """
    Ensure Alice and Bob synchronize __node_lists__ correctly.
    """

    await asyncio.sleep(2)  # allow propagation

    alice_data = await alice_server.get_data("__node_lists__", default=[])
    bob_data = await bob_server.get_data("__node_lists__", default=[])

    assert "Alice" in alice_data
    assert "Bob" in alice_data

    assert "Alice" in bob_data
    assert "Bob" in bob_data


@pytest.mark.asyncio
async def test_http_endpoints_reflect_cluster_state():
    """
    Ensure HTTP API returns replicated state.
    """

    async with httpx.AsyncClient() as client:
        r1 = await client.get("http://127.0.0.1:8000/")
        r2 = await client.get("http://127.0.0.1:8001/")

    data1 = r1.json()["data"]
    data2 = r2.json()["data"]

    assert "Alice" in data1
    assert "Bob" in data1

    assert "Alice" in data2
    assert "Bob" in data2


@pytest.mark.asyncio
async def test_data_replication_after_update(alice_server, bob_server):
    """
    Ensure arbitrary data propagates correctly.
    """

    await alice_server.put_data({"key1": "value1"})

    await asyncio.sleep(2)

    value = await bob_server.get_data("key1")

    assert value == "value1"