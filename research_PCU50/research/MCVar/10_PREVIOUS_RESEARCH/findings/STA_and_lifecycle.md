# COM Threading and Lifecycle

## Static evidence

Both MCVar registration resources specify `ThreadingModel=Apartment` for the Var2 class. This is a deployment clue, not a complete runtime threading contract. The Trace alias is registered `Both`, but it is not evidence that Var2 reads are free-threaded.

## Conservative client state machine

```text
DISCONNECTED -> CONNECTING -> CONNECTED -> DEGRADED -> RECONNECTING
                                      \-> DISCONNECTED
```

The transition implementation belongs to a single COM-owning worker. Reads are serialized, batches are bounded, retries are finite, and reconnect is explicit. A failed call must not start unbounded concurrent retries or silently discard per-item outcomes.

## Unknown until Windows validation

- STA initialization and message-pump requirements.
- Interface marshaling and cross-thread calls.
- Reentrancy during async/cyclic callbacks.
- Concurrent instances/processes and server sharing.
- COM server restart behavior.
- Exact SAFEARRAY/VARIANT ownership and cleanup from Automation.

## SDK implementation

`MCVAR_SDK/acquisition/mcvar_sdk.py` provides a portable injected adapter seam with single-flight access, order-preserving batches, retries/reconnect, quality/freshness fields and polling registry. It is not a Windows COM adapter and must not be presented as one.
