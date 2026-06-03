# The Protocol

The synchronization of data follows a push-pull model triggered by data mutations (put_data, pop_data) or incoming network messages. The protocol relies on `sync_up_recv`, which compares incoming data against local state using `analyze_commit_diff( ... )`. Based on the analysis between the incoming data and the local data, the node either accepts, broadcasts or rejects the incoming data. 

- If the local state is behind the incoming state, the node accepts the incoming data, and broadcasts the data to the other nodes. 
- If the local state is ahead of the incoming state, the node broadcasts the excess state. 
- If the states divergerged, the node uses one of five policies: `accept`, `merge`, `warn`, `exception`, or `ignore`. These policies determine whether the node should attempt to combine the logs, overwrite its local state, or halt execution.

# Pseudocode

```
// =============================================================================
// MESH DISTRIBUTED MONOTONIC DICTIONARY — 2-PROCEDURE ALGORITHM
// =============================================================================
//
// NODE STATE:
//   node.commit_keys   : LIST<STRING>        // append-only UUID4 hex commit IDs
//   node.commit_values : LIST<Op>            // parallel ops; Op = (kind, args)
//   node.connections   : MAP<STRING, Socket> // peer_id → WebSocket
//   node.policy        : STRING              // "accept" | "merge" | "warn" | ...
//
// REPLAY(ops) → MAP:  replay a list of Ops into a key-value map
//   FOR EACH op IN ops:
//     "set"    → state[op.args[0]] ← op.args[1]
//     "del"    → REMOVE op.args[0] FROM state
//     "update" → FOR EACH (k,v) IN op.args[0]: state[k] ← v
//     "clear"  → state ← {}
//   RETURN state
// =============================================================================


ASYNC PROCEDURE WRITE(node, key, value):

    // 1. Append a "set" op to the local commit log
    APPEND uuid4().hex              TO node.commit_keys
    APPEND Op("set", (key, value)) TO node.commit_values

    // 2. Serialize and broadcast the full log to all peers
    payload ← JSON_ENCODE({ "keys": node.commit_keys,
                             "ops" : node.commit_values })
    FOR EACH peer IN node.connections:
        AWAIT peer.send(payload)
    END FOR

END PROCEDURE


ASYNC PROCEDURE RECEIVE(node, sender, raw_payload):

    // 1. Decode incoming commit log
    obj           ← JSON_DECODE(raw_payload)
    inc_keys      ← obj["keys"]
    inc_ops       ← obj["ops"]

    local_set     ← SET(node.commit_keys)
    incoming_set  ← SET(inc_keys)

    // 2. Classify the commit-set relationship
    IF local_set == incoming_set THEN RETURN END IF   // already in sync

    IF   incoming_set ⊇ local_set  THEN status ← "ahead"
    ELIF local_set    ⊇ incoming_set THEN status ← "behind"
    ELSE                                  status ← "divergent"
    END IF

    // 3. Build propagation target list (everyone except sender, by default)
    peers ← COPY(KEYS(node.connections)) \ {sender}

    // 4. Resolve
    IF status == "ahead" THEN
        // Absorb commits we are missing (set-union, preserve order)
        FOR EACH (cid, op) IN zip(inc_keys, inc_ops):
            IF cid NOT IN local_set THEN
                APPEND cid TO node.commit_keys
                APPEND op  TO node.commit_values
            END IF
        END FOR

    ELIF status == "behind" THEN
        // We are ahead — push our state back to sender
        APPEND sender TO peers
        // node log is unchanged

    ELSE  // divergent
        IF node.policy == "warn"      THEN WARN("CRDT divergence");   RETURN  END IF
        IF node.policy == "exception" THEN RAISE Exception("CRDT divergence") END IF
        IF node.policy == "ignore"    THEN RETURN                             END IF

        WARN("CRDT divergence")
        APPEND sender TO peers   // sender needs the reconciled result too

        IF node.policy == "accept" THEN
            // Set-union: absorb commits we are missing
            FOR EACH (cid, op) IN zip(inc_keys, inc_ops):
                IF cid NOT IN local_set THEN
                    APPEND cid TO node.commit_keys
                    APPEND op  TO node.commit_values
                END IF
            END FOR

        ELIF node.policy == "merge" THEN
            // Last-write-wins union: replay both sides, incoming wins on conflict
            reconciled ← { **REPLAY(node.commit_values), **REPLAY(inc_ops) }

            // Concatenate both logs, then append one reconciliation op
            node.commit_keys   ← node.commit_keys   + inc_keys
            node.commit_values ← node.commit_values + inc_ops
            APPEND uuid4().hex                    TO node.commit_keys
            APPEND Op("update", (reconciled,))    TO node.commit_values
        END IF

    END IF

    // 5. Serialize updated log and push to all target peers
    payload ← JSON_ENCODE({ "keys": node.commit_keys,
                             "ops" : node.commit_values })
    FOR EACH peer_id IN peers:
        AWAIT node.connections[peer_id].send(payload)
    END FOR

END PROCEDURE

// =============================================================================
// CONVERGENCE:
//   commit_keys only ever grows. Each RECEIVE strictly increases |local_set|
//   (status="ahead") or appends a reconciliation op (status="divergent").
//   After each change, the updated log is re-broadcast. Since |local_set| is
//   bounded by the total number of writes across all nodes, the protocol
//   terminates and all nodes converge to the same replayed state.
// =============================================================================
```