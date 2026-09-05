# Product Stage8 binding proof contract

Status: **implemented live-registry discovery/verifier; exact newer-core runtime binding still not observed**.

This document records the boundary after the live execution-contract increment. It must not be read as evidence that a particular Stage8 operation exists in the incomplete public Stage8 payload.

## Why this exists

The active Product profile freezes a concrete Stage8 implementation and adapter descriptor, while the public newer Stage8 source payload is incomplete. A historical stage contract, parser command name or string found in an API mapping is therefore not enough evidence to execute Product Mode.

Workbench now separates four levels explicitly:

1. **live registry execution contract** — current registry metadata publishes the selected stage key and `required_inputs`;
2. **candidate** — a parser path or callable-mapping key was observed;
3. **structured callable evidence** — the exact runtime exposes a callable with module, qualname, signature and inspectable source SHA-256;
4. **verified Stage8 binding** — callable metadata and the frozen live registry contract agree exactly.

Only level 4 may advance the unified Product state toward Stage8 execution.

## Product Profile / preflight execution identity

Product Profile schema `rocketdict-workbench-product-profile/6` carries explicit `required_inputs` from the live registry. Implementation-level metadata wins when present; explicit stage-level metadata is accepted as a fallback. Missing metadata remains `None` instead of being inferred.

Product preflight schema `rocketdict-workbench-product-preflight/2` requires the selected Stage8, 10, 12, 14, 16, 17 and 19 stages to expose both `stage_key` and a valid `required_inputs` list. Each selected upstream stage freezes:

- stage number and stage key;
- implementation;
- adapter descriptor;
- Product parameters hash;
- ordered `required_inputs`;
- `execution_contract_sha256` over the full current execution contract.

The Product preflight fingerprint therefore changes if the live execution-input contract changes.

Historical RocketDict evidence showed that stage runners previously represented required inputs explicitly, but historical values are **not** copied into current Product identity. If the current live registry does not publish the contract, preflight fails closed.

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
  - `adapter_descriptor_hash` / `descriptor_hash`;
  - `required_inputs`.

The probe fingerprint covers these observations. Persisted probe evidence is hashed again by the unified Product state.

## Read-only Stage8 discovery

Run:

```bash
rocketdict-workbench product-run-discover-stage8 ./my-project \
  --state ./my-project/experiments/product-run/<fingerprint>.json
```

`rocketdict-workbench-stage8-binding-discovery/1` compares **every structured callable** with the frozen Stage8 contract and returns:

- expected Stage8 stage/implementation/descriptor/parameter/input contract;
- structured callable count;
- exact matches;
- per-candidate mismatch reasons;
- status `unique_exact_match`, `no_exact_match`, or `ambiguous_exact_matches`.

Discovery does not mutate Product state and explicitly records that parser/string candidates are not execution proof.

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
- Product profile and frozen preflight agree on Stage8 key, implementation, descriptor, parameters and `required_inputs`;
- `execution_contract_sha256` recomputes exactly from the profile;
- the operation appears exactly once as a structured callable, not merely as a parser/candidate string;
- callable source is inspectable and has a SHA-256;
- callable metadata explicitly says Stage 8;
- callable stage key, implementation, descriptor hash and required inputs exactly match the frozen current registry contract;
- Workbench can resolve every frozen Stage8 input from the Product root.

For the first Stage8 slice, Workbench currently knows how to resolve exactly `document_version_id`. Therefore a current live registry contract other than `required_inputs=["document_version_id"]` is an explicit hard stop until support for the new input contract is implemented. This is a Workbench resolver capability, not a historical assertion about the current core.

The resulting `rocketdict-workbench-upstream-binding/2` record binds the frozen `document_version_id`, execution-contract hash, preflight fingerprint, Product-run root fingerprint, registry hash, RocketDict/API versions, API-probe fingerprint, operation identity and callable source identity.

A repeated verification of the same immutable evidence is idempotent. Mutation of a persisted binding or reuse of the obsolete binding-proof schema fails closed.

## What is deliberately not claimed yet

The dependency-light CI suite proves profile/preflight contract propagation, discovery, verifier and state-transition behavior with controlled evidence. It does **not** prove that the missing newer RocketDict core currently exposes a callable carrying the required Stage8 metadata.

Therefore the next milestone is not to invent an operation name or copy historical required inputs. It is to run Product preflight/probe against the exact recoverable/newer core runtime and either:

- obtain a current live Stage8 execution-input contract and a unique exact callable, then promote it; or
- record that the current public contract is absent/incompatible and recover/add that public core execution contract before any Stage8 Product execution is attempted.

Only after a real binding is promoted should Workbench implement the resumable Stage8 invocation and validate its durable output identity before continuing to the next upstream stage.
