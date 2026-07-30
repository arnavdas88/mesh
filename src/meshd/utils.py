import enum
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from .monotonic_dict import MonotonicDict


def convert_to_websocket(url: str) -> str:
    # 1. Parse the URL into components
    parsed = urlparse(url)
    
    # 2. Define the protocol mapping
    scheme_mapping = {
        'http': 'ws',
        'https': 'wss'
    }
    
    # 3. Get the new scheme (keep original if it's already ws/wss or not http/s)
    new_scheme = scheme_mapping.get(parsed.scheme, parsed.scheme)
    
    # 4. Rebuild the URL with the new scheme
    # parsed._replace() creates a modified copy of the NamedTuple
    updated_parsed = parsed._replace(scheme=new_scheme)
    
    return urlunparse(updated_parsed)

def connect_all(node_lists: list):
    for node_a in node_lists:
        for node_b in node_lists:
            if node_a != node_b:
                node_a.connect(node_b)
                node_b.connect(node_a)


def is_A_greater_than_B(A, B):
    """
    Returns commit IDs present in A but not in B.
    CRDT-safe (set difference).
    """
    return set(A._commit_keys) - set(B._commit_keys)

def A_minus_B(A: MonotonicDict, B: MonotonicDict):
    """
    Returns operations in A not present in B.
    """
    missing = set(A._commit_keys) - set(B._commit_keys)
    for key, op in zip(A._commit_keys, A._commit_values):
        if key in missing:
            yield key, op

class CommitStatus(enum.StrEnum):
    SAME = "same"
    AHEAD = "ahead"
    BEHIND = "behind"
    DIVERGENT = "divergent"

@dataclass(frozen=True)
class CommitAnalysis:
    status: CommitStatus = "same"
    last_common_commit: str = ""
    message: str = ""


def analyze_commit_diff(A: MonotonicDict, B: MonotonicDict):
    commits_A = set(A._commit_keys)
    commits_B = set(B._commit_keys)

    if commits_A == commits_B:
        return CommitAnalysis(
            status=CommitStatus.SAME,
            message="All commits are already synced."
        )

    if commits_A.issuperset(commits_B):
        return CommitAnalysis(
            status=CommitStatus.AHEAD,
            message=f"A is ahead by {len(commits_A - commits_B)} commits"
        )

    if commits_B.issuperset(commits_A):
        return CommitAnalysis(
            status=CommitStatus.BEHIND,
            message=f"A is behind by {len(commits_B - commits_A)} commits"
        )

    return CommitAnalysis(
        status=CommitStatus.DIVERGENT,
        message="Both replicas have unique commits (CRDT divergence)"
    )
