from __future__ import annotations

from collections import OrderedDict
from collections.abc import MutableMapping, Mapping

from dataclasses import dataclass

from typing import Any, Dict, Tuple, Optional

import uuid


@dataclass(frozen=True)
class Op:
    """Represents a single log operation."""
    kind: str            # 'set', 'del', 'update', 'clear'
    args: Tuple[Any, ...]

class MonotonicDict(MutableMapping):
    """
    A dictionary-like object whose *true* state is defined by an append-only,
    monotonically ordered log of operations.

    - Each mutating operation appends an Op to the log keyed by a UUID.
    - Any read operation materializes the dictionary by replaying the log.
    """

    def __init__(self, *args, **kwargs):
        # Monotonic ordered log: UUID -> Op
        self._commit_keys: list[str] = []
        self._commit_values: list[Op] = []

        if args or kwargs:
            # Use our own update, which will be logged.
            self.update(*args, **kwargs)

        self._materialized_cache: Dict[Any, Any] = {}
        self._materialized_cursor = None

    def _append_op(self, op: Op) -> None:
        """Append a new operation to the log (monotonic, append-only)."""
        op_id = uuid.uuid4().hex

        self._commit_keys.append(op_id)
        self._commit_values.append(op)

    def _materialize(self) -> Dict[Any, Any]:
        """
        Rebuild the effective dictionary state from the log.
        This is done fresh on every read as per the requirements.
        """

        _commits = self._commit_keys
        _operations = self._commit_values

        if _commits and _commits[-1] == self._materialized_cursor:
            return self._materialized_cache

        if self._materialized_cursor in self._commit_keys:
            _idx_cursor = _commits.index(self._materialized_cursor)
        else:
            _idx_cursor = -1
        
        _pending_commits = _commits[_idx_cursor + 1: ]
        _pending_ops = _operations[_idx_cursor + 1: ]

        for commit, op in zip(_pending_commits, _pending_ops):
            if op.kind == "set":
                key, value = op.args
                self._materialized_cache[key] = value
            elif op.kind == "del":
                (key,) = op.args
                self._materialized_cache.pop(key, None)
            elif op.kind == "update":
                (mapping,) = op.args
                for k, v in mapping.items():
                    self._materialized_cache[k] = v
            elif op.kind == "clear":
                self._materialized_cache.clear()
            else:
                raise ValueError(f"Unknown op kind: {op.kind}")

            self._materialized_cursor = commit

        return self._materialized_cache

    def to_dict(self) -> Dict[Any, Any]:
        """Convenience: get the current materialized state as a regular dict."""
        return self._materialize()

    def __getitem__(self, key: Any) -> Any:
        state = self._materialize()
        return state[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._append_op(Op("set", (key, value)))

    def __delitem__(self, key: Any) -> None:
        # To respect normal dict semantics, we first verify key exists.
        state = self._materialize()
        if key not in state:
            raise KeyError(key)
        self._append_op(Op("del", (key,)))

    def __iter__(self):
        state = self._materialize()
        return iter(state)

    def __len__(self) -> int:
        return len(self._commit_keys)

    def __contains__(self, key: object) -> bool:
        state = self._materialize()
        return key in state

    def get(self, key: Any, default: Optional[Any] = None) -> Any:
        state = self._materialize()
        return state.get(key, default)

    def clear(self) -> None:
        """Logically clear the dictionary (but keep the commit append-only)."""
        self._append_op(Op("clear", ()))

    def update(self, *args, **kwargs) -> None:
        """
        Log an 'update' operation. We collect the data into a mapping and
        append a single Op('update').
        """
        mapping: Dict[Any, Any] = {}

        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 positional argument")
            other = args[0]
            if isinstance(other, Mapping):
                mapping.update(other)
            else:
                # Assume an iterable of (key, value)
                for k, v in other:
                    mapping[k] = v

        if kwargs:
            mapping.update(kwargs)

        if mapping:
            self._append_op(Op("update", (mapping,)))

    def commit_history(self) -> OrderedDict[str, Op]:
        """Returns the commit history of the dict."""
        return OrderedDict(zip(self._commit_keys, self._commit_values))

    @property
    def last_commit(self, ) -> str:
        '''Get the last commit
        '''
        return self._commit_keys[-1] if self._commit_keys else None

    def fork(self, commit: str):
        if commit not in self._commit_keys:
            raise Exception()
        _commit_idx = self._commit_keys.index(commit)

        _forked_mdict = MonotonicDict()
        _forked_mdict._commit_keys = self._commit_keys[:_commit_idx + 1]
        _forked_mdict._commit_values = self._commit_values[:_commit_idx + 1]

        return _forked_mdict

    def merge(self, incoming_data):
        pass

    def __eq__(self, other: object) -> bool:
        """
        Equality compares materialized states. Supports comparison with
        regular dicts and other mappings.
        """
        if isinstance(other, MonotonicDict):
            return self.to_dict() == other.to_dict()
        if isinstance(other, Mapping):
            return self.to_dict() == dict(other)
        return NotImplemented

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.to_dict()!r})"
    
