import asyncio
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

async def node_server(name: str, port: int, join_urls=None):

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
        node_lists = await node.get_data("__node_lists__", default=[])
        await node.put_data({"__node_lists__": node_lists + [name]})

        yield

    app = FastAPI(lifespan=lifespan)
    node = Node(name=name, app=app)

    @app.get("/")
    async def root():
        node_lists = await node.get_data("__node_lists__", default=[])
        return {"name": name, "data": node_lists}

    server = UvicornTestServer(app, port=port)
    await server.start()

    yield node

    await server.stop()
    yield


# -------------------------------------------------
# Main Simulation
# -------------------------------------------------

async def main():

    # ---------------------------------------------
    # PARTITION A (4 nodes)
    # ---------------------------------------------

    alice_fixture = node_server("Alice", 8000)
    alice = await alice_fixture.__anext__()

    bob_fixture = node_server("Bob", 8001, ["ws://127.0.0.1:8000/mesh"])
    bob = await bob_fixture.__anext__()

    charlie_fixture = node_server("Charlie", 8002, ["ws://127.0.0.1:8000/mesh"])
    charlie = await charlie_fixture.__anext__()

    dan_fixture = node_server("Dan", 8003, ["ws://127.0.0.1:8000/mesh"])
    dan = await dan_fixture.__anext__()

    await asyncio.sleep(3)

    # Validate Partition A
    alice_data = await alice.get_data("__node_lists__", default=[])
    bob_data = await bob.get_data("__node_lists__", default=[])
    charlie_data = await charlie.get_data("__node_lists__", default=[])
    dan_data = await dan.get_data("__node_lists__", default=[])

    assert "Alice" in alice_data
    assert "Bob" in alice_data
    assert "Charlie" in alice_data
    assert "Dan" in alice_data

    assert "Alice" in bob_data
    assert "Bob" in bob_data
    assert "Charlie" in bob_data
    assert "Dan" in bob_data


    # ---------------------------------------------
    # PARTITION B (4 nodes)
    # ---------------------------------------------

    ema_fixture = node_server("Ema", 8010)
    ema = await ema_fixture.__anext__()

    fargo_fixture = node_server("Fargo", 8011, ["ws://127.0.0.1:8010/mesh"])
    fargo = await fargo_fixture.__anext__()

    george_fixture = node_server("George", 8012, ["ws://127.0.0.1:8010/mesh"])
    george = await george_fixture.__anext__()

    hannah_fixture = node_server("Hannah", 8013, ["ws://127.0.0.1:8010/mesh"])
    hannah = await hannah_fixture.__anext__()

    await asyncio.sleep(3)

    # Validate Partition B
    ema_data = await ema.get_data("__node_lists__", default=[])
    fargo_data = await fargo.get_data("__node_lists__", default=[])
    george_data = await george.get_data("__node_lists__", default=[])
    hannah_data = await hannah.get_data("__node_lists__", default=[])

    assert "Ema" in ema_data
    assert "Fargo" in ema_data
    assert "George" in ema_data
    assert "Hannah" in ema_data

    assert "Ema" in fargo_data
    assert "Fargo" in fargo_data
    assert "George" in fargo_data
    assert "Hannah" in fargo_data


    # Bridge connection (connect Alice to Ema)
    await alice.join(["ws://127.0.0.1:8010/mesh"])

    await asyncio.sleep(2)  # allow merge + propagation
    await asyncio.sleep(2)  # allow merge + propagation



    # NOTE : Not work beyond this, as commits diverged due to keeping the nodes name data in the same monotonic dictionary.
    # -------------------------------------------------
    # Final Full Mesh Validation
    # -------------------------------------------------

    final_alice = await alice.get_data("__node_lists__", default=[])
    final_bob = await bob.get_data("__node_lists__", default=[])
    final_charlie = await charlie.get_data("__node_lists__", default=[])
    final_dan = await dan.get_data("__node_lists__", default=[])

    final_ema = await ema.get_data("__node_lists__", default=[])
    final_fargo = await fargo.get_data("__node_lists__", default=[])
    final_george = await george.get_data("__node_lists__", default=[])
    final_hannah = await hannah.get_data("__node_lists__", default=[])

    # Check global convergence
    assert "Alice" in final_hannah
    assert "Bob" in final_hannah
    assert "Charlie" in final_hannah
    assert "Dan" in final_hannah

    assert "Ema" in final_alice
    assert "Fargo" in final_alice
    assert "George" in final_alice
    assert "Hannah" in final_alice


    print("Full mesh convergence successful.")


    # -------------------------------------------------
    # Cleanup
    # -------------------------------------------------

    await alice_fixture.__anext__()
    await bob_fixture.__anext__()
    await charlie_fixture.__anext__()
    await dan_fixture.__anext__()

    await ema_fixture.__anext__()
    await fargo_fixture.__anext__()
    await george_fixture.__anext__()
    await hannah_fixture.__anext__()


if __name__ == "__main__":
    asyncio.run(main())