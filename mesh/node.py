import asyncio
import websockets
from fastapi import WebSocket
from typing import Dict, List, Optional

from .monotonic_dict import MonotonicDict
from .utils import analyze_commit_diff
from .transport import (
    WebSocketProtocol,
    serialize_monotonic_dict,
    deserialize_monotonic_dict
)


class BaseMeshNode:
    """
    Base abstraction for a distributed mesh node.

    Responsibilities:
    - Manage peer connections
    - Maintain replicated MonotonicDict state
    - Perform state synchronization
    """

    def __init__(self, name: Optional[str] = None):
        self.name = name

        # Active websocket connections:
        # key   -> peer identifier (URL or client address string)
        # value -> WebSocketProtocol wrapper
        self.connections: Dict[str, WebSocketProtocol] = {}

        # Replicated state
        self.data = MonotonicDict()

    def __repr__(self):
        return f"<Node {self.name} connections({list(self.connections.keys())})>"

    # ------------------------------------------------------------------
    # Synchronization Layer
    # ------------------------------------------------------------------

    async def sync_up(self, nodes_list: Optional[List[str]] = None):
        """
        Push local state to selected peers.

        If no list is provided, sync with all connected peers.
        """
        if not nodes_list:
            nodes_list = list(self.connections.keys())

        for node in nodes_list:
            await self.send(node, self.data)

    async def sync_up_recv(self, sender: str, incoming_data: MonotonicDict):
        """
        Handle incoming state and resolve commit differences.
        """
        analysis = analyze_commit_diff(incoming_data, self.data)

        if analysis.status == "same":
            return

        # List of peers to propagate changes to
        peers = list(self.connections.keys())

        if sender in peers:
            peers.remove(sender)

        if analysis.status == "ahead":
            # Remote state is ahead → adopt it
            self.data._commit_keys = incoming_data._commit_keys
            self.data._commit_values = incoming_data._commit_values

        elif analysis.status == "behind":
            # Remote state is behind → push ours back to sender
            peers.append(sender)

        else:
            raise Exception(analysis.message)

        await self.sync_up(peers)

    # ------------------------------------------------------------------
    # Transport Layer
    # ------------------------------------------------------------------

    async def send(self, peer: str, data: MonotonicDict):
        """
        Send serialized state to a peer.
        """
        if peer not in self.connections:
            return

        ws = self.connections[peer]
        payload = serialize_monotonic_dict(data)

        try:
            await ws.send_text(payload)
        except Exception as ex:
            # Silent failure (unchanged behavior)
            pass

    async def recv(self, peer: str, raw_payload: str):
        """
        Receive serialized state from peer and trigger sync logic.
        """
        incoming_data = deserialize_monotonic_dict(raw_payload)
        await self.sync_up_recv(peer, incoming_data)

    # ------------------------------------------------------------------
    # Public Data API
    # ------------------------------------------------------------------

    async def put_data(self, key_value_pairs: Dict):
        """
        Insert/update key-value pairs and propagate changes.
        """
        for key, value in key_value_pairs.items():
            self.data[key] = value

        await self.sync_up()

    async def get_data(self, key, default=None):
        """
        Retrieve value after ensuring sync.
        """
        await self.sync_up()
        return self.data.get(key, default)

    async def pop_data(self, key, default=None):
        """
        Remove key if present and propagate change.
        """
        if key in self.data:
            value = self.data.pop(key)
            await self.sync_up()
            return value

        return default


# ----------------------------------------------------------------------
# FastAPI-Integrated Node
# ----------------------------------------------------------------------

class Node(BaseMeshNode):
    """
    FastAPI-enabled mesh node.

    Extends BaseMeshNode by:
    - Registering WebSocket route
    - Accepting inbound connections
    """

    def __init__(self, name=None, app=None, client=None):
        super().__init__(name=name)

        self.app = app
        self.client = client

        # Register websocket endpoint if FastAPI app provided
        if self.app:
            self._register_routes()

    def _register_routes(self):
        """
        Register `/mesh` websocket endpoint for inbound connections.
        """

        @self.app.websocket("/mesh")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()

            peer = str(websocket.client)
            self.connections[peer] = WebSocketProtocol(websocket)

            try:
                while True:
                    data = await websocket.receive_text()
                    await self.recv(peer, data)
            except Exception as ex:
                # Silent disconnect handling (unchanged behavior)
                pass
    

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    async def join(self, urls: List[str], token: str = ""):
        """
        Connect to remote mesh nodes via WebSocket.

        Args:
            urls: List of websocket URLs
            token: (unused for now – reserved for auth)
        """
        for url in urls:
            ws = await websockets.connect(url)

            # Store connection wrapper
            self.connections[url] = WebSocketProtocol(ws)

            # Spawn background listener task
            asyncio.create_task(self._listen(ws, url))

        await asyncio.sleep(1)

        await self.sync_up()

    async def _listen(self, ws, peer_id: str):
        """
        Background listener for an outgoing websocket connection.
        """
        try:
            async for message in ws:
                await self.recv(peer_id, message)
        except Exception as ex:
            # Silent failure (same logic as original)
            pass
