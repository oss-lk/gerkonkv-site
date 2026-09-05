# Product Stage8 binding proof contract

Status: **implemented verifier; exact newer-core runtime binding still not observed**.

This document records the boundary after the structured API-probe increment. It must not be read as evidence that a particular Stage8 operation exists in the incomplete public Stage8 payload.

## Why this exists

The active Product profile freezes a concrete Stage8 implementation and adapter descriptor, while the public Stage8 source payload is incomplete. A parser command name or a string found in an API mapping is therefore not enough evidence to execute Product Mode.

Workbench now separates three levels explicitly:

1. **candidate** — a parser path or callable-mapping key was observed;
2. **structured callable evidence** — the exact runtime exposes a callable with module, qualname, signature and inspectable source SHA-256;
3. **verified Stage8 binding** — the callable itself publishes binding metadata matching the frozen Product profile exactly.

Only level 3 may advance the unified Product state toward Stage8 execution.

## Probe schema v2

`rocketdict-core-api-surface-probe/2` records each callable mapping entry with:

- mapping module and mapping name;
- exact operation key;
- callable module and qualname;
- `inspect.signature` text plus structured parameter names/kinds/required flags;
- SHA-256 of inspectable callable source;
- explicit callable metadata, when published by the runtime:
  - `stage_number`;
  - `stage_key`;
  - `implementation_key`;
  - `adapter_descriptor_hash`;
  - `required_inputs`.

The probe fingerprint covers these observations. Persisted probe evidence is hashed again by the unified Product state.

## Stage8 promotion rules

`verify_stage8_binding(...)` and the CLI command

```bash
rocketdict-workbench product-run-bind-stage8 ./my-project \
  --state ./my-project/experiments/product-run/<fingerprint>.json \
  --operation <exact-operation-key>
```

fail closed unless all of the following are true:

- the Product run contains unmodified completed preflight evidence;
- the Product run contains unmodified probe-v2 evidence;
- the probe's internal fingerprint recomputes exactly;
- probed RocketDict/API versions equal the preflight identity;
- the operation appears exactly once as a **structured callable**, not merely as a parser/candidate string;
- callable source is inspectable and has a SHA-256;
- the frozen Product Stage8 implementation and descriptor identities are present and internally consistent;
- callable metadata explicitly says Stage 8;
- callable `stage_key`, implementation and descriptor hash exactly match Product preflight/profile;
- Stage8 required inputs are exactly `document_version_id`;
- the frozen `document_version_id` is persisted in the resulting binding.

The resulting `rocketdict-workbench-upstream-binding/1` record also binds the preflight fingerprint, Product-run root fingerprint, registry hash, RocketDict version, API version and API-probe fingerprint.

A repeated verification of the same immutable evidence is idempotent. Mutation of an already persisted binding fails closed.

## What is deliberately not claimed yet

The dependency-light CI suite proves the verifier and state-transition contract with controlled evidence. It does **not** prove that the missing newer RocketDict core currently exposes a callable carrying the required Stage8 metadata.

Therefore the next milestone is not to invent an operation name. It is to run `product-run-init` against the exact recoverable/newer core runtime, inspect `callable_operations`, and either:

- promote a matching Stage8 callable with `product-run-bind-stage8`, or
- record that no such public binding exists and recover/add the missing public core execution contract before any Stage8 Product execution is attempted.

Only after a real binding is promoted should Workbench implement the resumable Stage8 invocation and validate its durable output identity before continuing to the next upstream stage.
