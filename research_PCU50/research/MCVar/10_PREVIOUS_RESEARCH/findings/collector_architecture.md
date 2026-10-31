# Architecture

```text
NiceGUI or other client
        |
Monitoring service / API
        |
SubscriptionRegistry (polling-backed today)
        |
AcquisitionClient: batching, single-flight, retry/reconnect, freshness
        |
ReadOnlyAdapter boundary
        |
Windows x86 MCVar COM adapter (NOT IMPLEMENTED/VALIDATED HERE)
        |
MCVar.Var2 -> NC/PLC provider
```

The boundary is intentionally opaque because Phase 12 did not prove MCVar-to-NCDDE transport, and Phase 13 has no Windows COM runtime. The application can still implement tested orchestration, result normalization, bounded scheduling and mock/UI integration without copying vendor protocol assumptions.

Native `ReadVarAsync`/`ReadVarCyclic` names are capability leads. The SDK does not call them and labels all subscriptions polling-backed until TypeInfo/runtime callback validation is complete.

Deployment recommendation: keep the eventual x86 COM collector on the PCU or an authorized Windows host where MCVar is registered; expose a narrow read-only application bridge to an external monitoring service. Remote COM/DCOM is not assumed supported or secure. Validate exact installation identity, apartment lifecycle and network/security policy separately.
