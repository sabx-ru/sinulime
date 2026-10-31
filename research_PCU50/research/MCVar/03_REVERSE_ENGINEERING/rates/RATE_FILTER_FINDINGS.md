# Stage 16.7 Rate and Filter Findings

## Scope and result

Rate/filter semantics are **not established** by the available static evidence. Do not infer behavior from method names, log strings, or fragments that resemble a `VT_BOOL` bitmask.

## Available evidence

Both old and new target string inventories contain the same IVarX `CalculateRequestRates` log/method labels (old at `0x00032de4`/`0x0003a828` and new at `0x00033e2c`/`0x0003b828`, respectively). The text is identical, with apparent address movement due to image layout. The PE section summaries describe image sections only. There are no target binaries, reliable rate/filter table entries, function bytes, call sites, or CFGs in the supplied stage artifacts.

## Findings and limitations

- **Old/new rate calculation difference:** None established. Matching labels do not establish matching rate calculation, aggregation, clamping, or scheduling behavior.
- **Rate entry reliability:** No reliable entries are available in this stage package to associate a rate or filter value with a concrete table schema, consumer, or control-flow decision.
- **Filter interpretation:** No semantics are assigned to apparent `VT_BOOL` mask fragments. Without validated entry boundaries, field mapping, and code references, such fragments cannot support claims about enabled/disabled filters or per-item behavior.
- **Compatibility impact:** Unknown from static evidence; no rate/filter compatibility difference can be asserted or ruled out.

## What would resolve this

Provide both old and new target images (or matched `CalculateRequestRates`/filter disassemblies plus referenced data), and reliable rate/filter entries with validated boundaries and cross-references. Then compare normalized code/CFG and data consumers. This report used offline artifacts only and did not invoke Windows tools, a collector, or DDE.
