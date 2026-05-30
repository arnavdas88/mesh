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
    alice_data = get_internal_data(alice.data)
    bob_data = get_internal_data(bob.data)
    charlie_data = get_internal_data(charlie.data)
    dan_data = get_internal_data(dan.data)

    assert "Alice" in str(alice_data)
    assert "Bob" in str(alice_data)
    assert "Charlie" in str(alice_data)
    assert "Dan" in str(alice_data)

    assert "Alice" in str(bob_data)
    assert "Bob" in str(bob_data)
    assert "Charlie" in str(bob_data)
    assert "Dan" in str(bob_data)


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
    ema_data = get_internal_data(ema.data)
    fargo_data = get_internal_data(fargo.data)
    george_data = get_internal_data(george.data)
    hannah_data = get_internal_data(hannah.data)

    assert "Ema" in str(ema_data)
    assert "Fargo" in str(ema_data)
    assert "George" in str(ema_data)
    assert "Hannah" in str(ema_data)

    assert "Ema" in str(fargo_data)
    assert "Fargo" in str(fargo_data)
    assert "George" in str(fargo_data)
    assert "Hannah" in str(fargo_data)


    # Bridge connection (connect Alice to Ema)
    await alice.join(["ws://127.0.0.1:8010/mesh"])

    await asyncio.sleep(2)  # allow merge + propagation
    await asyncio.sleep(2)  # allow merge + propagation

    igor_fixture = node_server("Igor", 8014, ["ws://127.0.0.1:8010/mesh"])
    igor = await igor_fixture.__anext__()




    # -------------------------------------------------
    # Final Full Mesh Validation
    # -------------------------------------------------

    final_alice = get_internal_data(alice.data)
    final_bob = get_internal_data(bob.data)
    final_charlie = get_internal_data(charlie.data)
    final_dan = get_internal_data(dan.data)

    final_ema = get_internal_data(ema.data)
    final_fargo = get_internal_data(fargo.data)
    final_george = get_internal_data(george.data)
    final_hannah = get_internal_data(hannah.data)

    # Check global convergence
    assert "Alice" in str(final_hannah)
    assert "Bob" in str(final_hannah)
    assert "Charlie" in str(final_hannah)
    assert "Dan" in str(final_hannah)

    assert "Ema" in str(final_alice)
    assert "Fargo" in str(final_alice)
    assert "George" in str(final_alice)
    assert "Hannah" in str(final_alice)

    assert "Igor" in str(final_hannah)
    assert "Igor" in str(final_alice)


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
    await igor_fixture.__anext__()


if __name__ == "__main__":
    asyncio.run(main())