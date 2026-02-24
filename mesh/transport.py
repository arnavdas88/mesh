import json
from typing import Dict
from .monotonic_dict import MonotonicDict, Op


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