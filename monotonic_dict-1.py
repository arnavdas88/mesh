from mesh.monotonic_dict import MonotonicDict
from datetime import datetime
from enum import StrEnum

import time

class DummyStatus(StrEnum):
    SUCCESS = 'success'
    FAILURE = 'failure'
    ERROR = 'error'

if __name__ == "__main__":
    # Create a monotonic commit-based dictionary and perform some operations.
    dict_1 = MonotonicDict()

    # Empty dict check
    assert dict_1 == {}

    # Dict with some values check
    dict_1["hello"] = "world!"
    dict_1["status"] = DummyStatus.SUCCESS

    assert dict_1 == {"hello": "world!", "status": "success"}
    assert len([(k,v) for k,v in dict_1.items()]) == 2

    # Dict with more values check
    dict_1["message"] = "'world!' successfully stored in 'hello'"
    assert len([(k,v) for k,v in dict_1.items()]) == 3

    # Fork Test
    dict_1["datetime"] = time.time() # UTC
    dict_1.to_dict()
    dict_1_commit = dict_1.last_commit # Last commit
    del dict_1["datetime"]

    dict_2 = dict_1.fork(dict_1_commit)
    assert "datetime" in dict_2

    # 1000 concurrent deletions and additions check
    # Long commit history
    for _ in range(1_000):
        del dict_1["message"]
        dict_1["message"] = "'world!' successfully stored in 'hello'"
    assert len([(k,v) for k,v in dict_1.items()]) == 3

    # Materialization time after long commit history
    # Calculate dictionary materialization time
    start = time.perf_counter_ns()
    for _ in range(1_00_000):
        status = dict_1['status']
    end = time.perf_counter_ns()
    print(f"{(end - start) / 1_000_000_000} s")
    assert (end - start) / 1_000_000_000 < 1
    
    # Calculate dictionary materialization time
    start = time.perf_counter_ns()
    for _ in range(1_00_000):
        dict_1.to_dict()
    end = time.perf_counter_ns()
    print(f"{(end - start) / 1_000_000_000} s")
    assert (end - start) / 1_000_000_000 < 1

