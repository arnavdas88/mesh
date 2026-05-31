import asyncio
import pytest
import uvicorn
import httpx

from fastapi import FastAPI
from contextlib import asynccontextmanager

from mesh.node import Node


# -------------------------------------------------
# Uvicorn Background Server
# -------------------------------------------------

class UvicornTestServer:
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


# -------------------------------------------------
# Reusable Node Generator
# -------------------------------------------------

async def node_server(name: str, port: int, join_urls=None, config = {}):

    join_urls = join_urls or []

    @asynccontextmanager
    async def lifespan(app: FastAPI):

        # Join partition peers (if any)
        if join_urls:
            await node.join(join_urls)
            await asyncio.sleep(1)

        # Sync initial state
        await node.sync_up()
        await asyncio.sleep(1)

        # Register self
        # node_lists = await node.get_data("__node_lists__", default=[])
        await node.put_data({f"__node_{name}__": {"name": name, "config": config}})

        yield

    app = FastAPI(lifespan=lifespan)
    node = Node(name=name, app=app, action_on_conflict="merge")

    @app.get("/")
    async def root():
        node_lists = await node.get_data("__node_lists__", default=[])
        return {"name": name, "data": node_lists}

    server = UvicornTestServer(app, port=port)
    await server.start()

    yield node

    await server.stop()
    yield


def get_internal_data(data):
    internal_data = []
    for k, v in data.to_dict().items():
        if k.startswith("__") and k.endswith("__"):
            internal_data.append(v)
    return internal_data



# @pytest.mark.asyncio
async def test_partition_merge_and_convergence():

    fixtures = []

    try:
        # -------------------------------------------------
        # PARTITION A
        # -------------------------------------------------

        alice_fixture = node_server("Alice", 8000)
        alice = await alice_fixture.__anext__()
        fixtures.append(alice_fixture)

        bob_fixture = node_server(
            "Bob", 8001,
            ["ws://127.0.0.1:8000/mesh"]
        )
        bob = await bob_fixture.__anext__()
        fixtures.append(bob_fixture)

        charlie_fixture = node_server(
            "Charlie", 8002,
            ["ws://127.0.0.1:8000/mesh"]
        )
        charlie = await charlie_fixture.__anext__()
        fixtures.append(charlie_fixture)

        dan_fixture = node_server(
            "Dan", 8003,
            ["ws://127.0.0.1:8000/mesh"]
        )
        dan = await dan_fixture.__anext__()
        fixtures.append(dan_fixture)

        await asyncio.sleep(3)

        partition_a_nodes = ["Alice", "Bob", "Charlie", "Dan"]

        for node in [alice, bob, charlie, dan]:
            data = str(get_internal_data(node.data))
            for member in partition_a_nodes:
                assert member in data

        # -------------------------------------------------
        # PARTITION B
        # -------------------------------------------------

        ema_fixture = node_server("Ema", 8010)
        ema = await ema_fixture.__anext__()
        fixtures.append(ema_fixture)

        fargo_fixture = node_server(
            "Fargo", 8011,
            ["ws://127.0.0.1:8010/mesh"]
        )
        fargo = await fargo_fixture.__anext__()
        fixtures.append(fargo_fixture)

        george_fixture = node_server(
            "George", 8012,
            ["ws://127.0.0.1:8010/mesh"]
        )
        george = await george_fixture.__anext__()
        fixtures.append(george_fixture)

        hannah_fixture = node_server(
            "Hannah", 8013,
            ["ws://127.0.0.1:8010/mesh"]
        )
        hannah = await hannah_fixture.__anext__()
        fixtures.append(hannah_fixture)

        await asyncio.sleep(3)

        partition_b_nodes = ["Ema", "Fargo", "George", "Hannah"]

        for node in [ema, fargo, george, hannah]:
            data = str(get_internal_data(node.data))
            for member in partition_b_nodes:
                assert member in data

        # -------------------------------------------------
        # BRIDGE THE PARTITIONS
        # -------------------------------------------------

        await alice.join(["ws://127.0.0.1:8010/mesh"])

        await asyncio.sleep(4)

        igor_fixture = node_server(
            "Igor",
            8014,
            ["ws://127.0.0.1:8010/mesh"]
        )
        igor = await igor_fixture.__anext__()
        fixtures.append(igor_fixture)

        await asyncio.sleep(4)

        # -------------------------------------------------
        # GLOBAL CONVERGENCE
        # -------------------------------------------------

        expected_nodes = [
            "Alice",
            "Bob",
            "Charlie",
            "Dan",
            "Ema",
            "Fargo",
            "George",
            "Hannah",
            "Igor",
        ]

        all_nodes = [
            alice,
            bob,
            charlie,
            dan,
            ema,
            fargo,
            george,
            hannah,
            igor,
        ]

        for node in all_nodes:
            data = str(get_internal_data(node.data))

            for expected in expected_nodes:
                assert expected in data, (
                    f"{expected} missing from {node.name}"
                )

    finally:
        # -------------------------------------------------
        # CLEANUP
        # -------------------------------------------------

        for fixture in reversed(fixtures):
            try:
                await fixture.__anext__()
            except StopAsyncIteration:
                pass