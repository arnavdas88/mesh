import json
import websockets
from fastapi import WebSocket
from typing import Dict
from .monotonic_dict import MonotonicDict, Op

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


def serialize_monotonic_dict(data: MonotonicDict) -> str:
    payload = {
        "commit_keys": data._commit_keys,
        "commit_values": [
            {"kind": op.kind, "args": op.args}
            for op in data._commit_values
        ],
    }
    return json.dumps(payload)


def deserialize_monotonic_dict(payload: str) -> MonotonicDict:
    raw = json.loads(payload)

    md = MonotonicDict()
    md._commit_keys = raw["commit_keys"]
    md._commit_values = [
        Op(kind=op["kind"], args=tuple(op["args"]))
        for op in raw["commit_values"]
    ]

    return md