import asyncio
import websockets
from fastapi import WebSocket
from typing import Dict, List
from .monotonic_dict import MonotonicDict
from .utils import analyze_commit_diff
from .transport import serialize_monotonic_dict, deserialize_monotonic_dict


class WebSocketProtocol:
    def __init__(self, ws : websockets.WebSocketClientProtocol | WebSocket):
        self.ws = ws
        self.ws_type = type(ws)
    
    async def send_text(self, data: str):
        if self.ws_type is websockets.ClientConnection:
            await self.ws.send(data)
        elif self.ws_type is WebSocket:
            await self.ws.send_text(data)
        else:
            pass

    def send(self, data):
        pass

class Node:
    def __init__(self, name=None, app=None, client=None):
        self.name = name
        self.app = app
        self.client = client

        # Instead of in-memory node refs, we store:
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}

        self.data = MonotonicDict()

        # Register websocket route
        if self.app:
            self._register_routes()

    def __repr__(self):
        return f"<Node {self.name} connections({list(self.connections.keys())})>"

    def _register_routes(self):
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
                pass

    async def join(self, urls: List[str], token: str = ""):
        for url in urls:
            ws = await websockets.connect(url, )
            self.connections[url] = WebSocketProtocol(ws)

            asyncio.create_task(self._listen(ws, url))

    async def _listen(self, ws, url):
        try:
            async for message in ws:
                await self.recv(url, message)
        except Exception as ex:
            pass

    async def sync_up(self, nodes_list=None):
        if not nodes_list:
            nodes_list = list(self.connections.keys())

        for node in nodes_list:
           await self.send(node, self.data)

    async def sync_up_recv(self, sender, incoming_data: MonotonicDict):
        analysis = analyze_commit_diff(incoming_data, self.data)

        if analysis.status == "same":
            return

        P = list(self.connections.keys())
        if sender in P:
            P.remove(sender)

        if analysis.status == "ahead":
            self.data._commit_keys = incoming_data._commit_keys
            self.data._commit_values = incoming_data._commit_values
        elif analysis.status == "behind":
            P.append(sender)
        else:
            raise Exception(analysis.message)

        await self.sync_up(P)

    async def send(self, node, data: MonotonicDict):
        """
        node: URL string
        data: MonotonicDict
        """
        if node not in self.connections:
            return

        ws = self.connections[node]
        payload = serialize_monotonic_dict(data)

        try:
            await ws.send_text(payload)
        except Exception as ex:
            pass

    async def recv(self, node, data):
        """
        node: sender identifier
        data: JSON serialized MonotonicDict
        """
        incoming_data = deserialize_monotonic_dict(data)
        await self.sync_up_recv(node, incoming_data)


    # Data functions
    async def put_data(self, key_value_pairs):
        for key, value in key_value_pairs.items():
            self.data[key] = value

        await self.sync_up()

    async def get_data(self, key, default = None):
        await self.sync_up()

        return self.data.get(key, default)

    async def pop_data(self, key, default = None):
        if key in self.data:
            _value = self.data.pop(key)
            await self.sync_up()
            return _value

        # raise NotImplementedError()
        return default