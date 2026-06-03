## Definitions

Let a *commit log* $L = [(c_1, o_1), (c_2, o_2), \ldots, (c_n, o_n)]$ be an ordered sequence of pairs where each $c_i \in \mathcal{U}$ is a UUID4 hex string (globally unique identifier) and each $o_i \in \{\text{set}(k,v),\ \text{del}(k),\ \text{update}(M),\ \text{clear}\}$ is an operation.

Let $\mathcal{M}(L)$ denote the *materialization* of log $L$: the map produced by replaying $L$ from left to right, where `set(k,v)` writes $k \mapsto v$, `del(k)` removes $k$, `update(M)` writes all pairs in $M$, and `clear` empties the map.

Let $\mathcal{C}(L) = \{c_i \mid (c_i, o_i) \in L\}$ denote the *commit set* of $L$.

Let a *node* $n_i$ hold a log $L_i$ and be connected to a set of peers. Define the *conflict policy* $\pi \in \{\text{accept},\ \text{merge},\ \text{warn},\ \text{exception},\ \text{ignore}\}$.

## Theorem (Soundness, Monotonicity, and Eventual Consistency)

Let $\mathcal{N} = \{n_1, n_2, \ldots, n_k\}$ be a set of mesh nodes, each holding a commit log $L_i$, communicating via the `sync_up` / `sync_up_recv` protocol with conflict policy $\pi \in \{\text{accept},\ \text{merge}\}$. Then the following properties hold jointly:


### P1 - Append-Only Monotonicity
For any node $n_i$ and any two times $t < t'$: $\mathcal{C}(L_i^t) \subseteq \mathcal{C}(L_i^{t'})$
No commit is ever removed from a log. Every write operation (`__setitem__`, `__delitem__`, `update`, `clear`) appends exactly one new entry with a fresh UUID to $L_i$, and `try_accept` / `merge` only append; they never delete.


### P2 - Global Uniqueness of Commit Identifiers
For any two distinct write events $e_1 \neq e_2$ occurring on any nodes $n_i, n_j \in \mathcal{N}$ (possibly $i = j$) at any times:
$c_{e_1} \neq c_{e_2} \quad \text{with overwhelming probability}$
since each $c \leftarrow \texttt{uuid4().hex}$ is drawn from a $2^{122}$-element space.


### P3 - Idempotency and Commutativity of `try_accept`
Let $\oplus$ denote the `try_accept` merge operator. For any logs $L_a, L_b, L_c$:
$L_a \oplus L_a = L_a \qquad \text{(idempotency)}$
$\mathcal{C}(L_a \oplus L_b) = \mathcal{C}(L_a) \cup \mathcal{C}(L_b) \qquad \text{(set-union on commit IDs)}$
$\mathcal{C}((L_a \oplus L_b) \oplus L_c) = \mathcal{C}(L_a \oplus (L_b \oplus L_c)) \qquad \text{(associativity)}$


### P4 - Materialization Correctness
For any log $L$ and any cursor position $j \leq |L|$, let $L_{[j:]}$ denote the suffix of $L$ from position $j$. Then:
$\mathcal{M}(L) = \mathcal{M}(L_{[0:j]}) \oplus_{\text{replay}} \mathcal{M}(L_{[j:]})$
where $\oplus_{\text{replay}}$ denotes sequential application. That is, the incremental cursor-based replay in `_materialize` produces the same result as a full replay from the beginning, for any valid cursor position.


### P5 - Merge Sanity (Key Preservation)
Let $L_{\text{merged}} = \text{merge}(L_a, L_b)$ or $L_{\text{merged}} = \text{accept}(L_a, L_b)$. Then `_check` guarantees:
$\forall k \in \text{dom}(\mathcal{M}(L_a)) \cup \text{dom}(\mathcal{M}(L_b)) : k \in \text{dom}(\mathcal{M}(L_{\text{merged}}))$
No key present in either input replica is absent from the merged result. If this condition fails, the merge is rejected and $L_i$ is left unchanged.


### P6 - Convergence (Eventual Consistency)
Assume the network is eventually reliable (every message is eventually delivered). After any finite sequence of write operations with no further writes, and with $\pi \in \{\text{accept},\ \text{merge}\}$:

$\exists\, T : \forall\, t > T,\ \forall\, n_i, n_j \in \mathcal{N} : \mathcal{M}(L_i^t) = \mathcal{M}(L_j^t)$

*Proof sketch:*

- By $P1$ $|\mathcal{C}(L_i)|$ is non-decreasing and bounded above by $\left|\bigcup_j \mathcal{C}(L_j)\right
- Each `sync_up_recv` invocation with status `ahead` applies `try_accept`, strictly increasing $|\mathcal{C}(L_i)|$ by at least 1 (by $P2$) no collision)
- Each `sync_up_recv` invocation with status `divergent` under `accept` applies `try_accept` (set-union); under `merge` it additionally appends a single reconciliation `update` op encoding $\mathcal{M}(L_a) \cup_{\text{LWW}} \mathcal{M}(L_b)$.
- After each merge, the updated node re-broadcasts to all peers via `sync_up`, propagating the enlarged log.
- Since the commit set is finite and strictly grows toward $\bigcup_j \mathcal{C}(L_j^0)$ at each step, the protocol terminates in at most $\sum_i |\mathcal{C}(L_i^0)|$ rounds.
- At termination, $\mathcal{C}(L_i) = \mathcal{C}(L_j)$ for all $i, j$, and since all nodes replay the same set of operations (with `merge` having appended a deterministic reconciliation op), $\mathcal{M}(L_i) = \mathcal{M}(L_j)$. $\blacksquare$


### P7 - Conflict Policy Monotonicity
The conflict policies form a partial order by the strength of convergence guarantee they provide:

$\text{merge} \geq \text{accept} \geq \text{warn} \geq \text{ignore} \geq \text{exception}$

Only `merge` and `accept` satisfy **P6**. `warn` and `ignore` preserve  **P1 - P5** locally but do not guarantee globconvergence. `exception` halts the protocol on divergence.


## Corollary (CRDT Classification)
Under policy `accept`, the `MonotonicDict` with `try_accept` as its join operator is a *state-based CRDT* (Conflict-free Replicated Data Type) with join semilattice $(\mathcal{P}(\mathcal{U}), \subseteq, \cup)$ over commit sets, satisfying the three CRDT laws: commutativity, associativity, and idempotency of the merge function (all established in **P3**). 