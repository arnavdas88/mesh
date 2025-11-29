import enum
from dataclasses import dataclass

from .monotonic_dict import MonotonicDict

def connect_all(node_lists: list):
    for node_a in node_lists:
        for node_b in node_lists:
            if node_a != node_b:
                node_a.connect(node_b)
                node_b.connect(node_a)


def is_A_greater_than_B(A, B):
    '''
    Returns elements from list A that list B does not have.
    '''

    for element in A:
        if element not in B:
            yield element
        
    return []

def A_minus_B(A, B):
    '''
    Returns elements from dict a that dict B does not have.
    '''
    for element, value in A.items():
        if element not in B:
            yield (element, value)
        
    return {}

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


def analyze_commit_diff(A:MonotonicDict, B:MonotonicDict):
    if A.last_commit == B.last_commit:
        return CommitAnalysis(message="All commits are already synced.") # Commits are equal

    if None in [A.last_commit, B.last_commit]:
        # Either one is empty
        if A.last_commit:
            return CommitAnalysis(
                status=CommitStatus.AHEAD, 
                last_common_commit=None,
                message=f"No new commits"
            )
        else:
            return CommitAnalysis(
                status=CommitStatus.BEHIND, 
                last_common_commit=None,
                message=f"Empty commits"
            )

    _status = None
    _diff_commits = 0
    _last_common_commit = None
    
    if A.last_commit in B.commit_history():
        _idx = B._commit_keys.index(A.last_commit)
        _diff_commits = len(B._commit_keys[_idx + 1 : ])
        _last_common_commit = B._commit_keys[_idx]
        _status = CommitStatus.BEHIND
        # A is monotonically behind B

    elif B.last_commit in A.commit_history():
        _idx = A._commit_keys.index(B.last_commit)
        _diff_commits = len(A._commit_keys[_idx + 1 : ])
        _last_common_commit = A._commit_keys[_idx]
        _status = CommitStatus.AHEAD
        # B is monotonically behind A

    else:
        # Commits have been diverged
        _last_common_commit = None
        _status = CommitStatus.DIVERGENT

        # Commits Example :
        # A ------ 1a --- 1b --- 1c --- 2a --- 2b --- 2c ---
        # B ------ 1a --- 1b --- 4a --- 4b ---
        #                         ^ (Commit diverged from here)
        # Merge Conflict

        _longest_commit_chain = max(len(A._commit_keys), len(B._commit_keys))

        for _commit_idx in range(_longest_commit_chain):
            if A._commit_keys[_commit_idx] != B._commit_keys[_commit_idx]:
                _last_common_commit = A._commit_keys[_commit_idx - 1]
                break


    if _status == CommitStatus.DIVERGENT:
        return CommitAnalysis(
            status=_status,
            last_common_commit=_last_common_commit,
            message=f"Commits are diverged from {_last_common_commit}"
        )
    else:
        return CommitAnalysis(
            status=_status,
            last_common_commit=_last_common_commit,
            message=f"Commits are {_status} by {_diff_commits} commits from {_last_common_commit}"
        )


