# BRK Container Format Specification v0.1

## Overview

**BRK** (Breakthrough Container) is a semantic / task-oriented reconstruction container format. It is **NOT** a universal lossless compressor. It does **NOT** break Shannon's theorem. It stores a contract-bound semantic specification for acceptable reconstruction.

**BRK は Shannon の定理を破るものではありません。**
**BRK は任意データを完全可逆圧縮する形式ではありません。**
**BRK は明示された契約に基づき、意味的・タスク的に十分な再構成仕様を保存する形式です。**

## File Extension

- **Extension**: `.brk`
- **MIME candidates**:
  - `application/vnd.brk`
  - `application/vnd.breakthrough-container`

## Magic Bytes

- **Magic**: `b"BRK1\n"` (5 bytes: `0x42 0x52 0x4B 0x31 0x0A`)
- The magic string is `"BRK1"` followed by a newline byte.

## Binary Structure

A `.brk` file consists of:

```
[MAGIC: 5 bytes] [CODEC_BYTE: 1 byte] [PAYLOAD: variable]
```

| Field        | Size        | Description                                    |
|--------------|-------------|------------------------------------------------|
| MAGIC        | 5 bytes     | `b"BRK1\n"`                                   |
| CODEC_BYTE   | 1 byte      | Payload compression codec identifier           |
| PAYLOAD      | variable    | Compressed canonical JSON                      |

## Codec Byte

| Value  | Description                        |
|--------|------------------------------------|
| `0x01` | zlib-compressed canonical UTF-8 JSON |

Only codec `0x01` is defined in this version. Unknown codec bytes MUST be rejected.

## Payload Format

The payload is canonical JSON (UTF-8) compressed with zlib at level 9.

Canonical JSON rules:
- `ensure_ascii=False`
- `sort_keys=True`
- `separators=(",", ":")` (no extra whitespace)
- UTF-8 encoded

Decompression: `zlib.decompress(PAYLOAD)` → canonical JSON bytes → `json.loads()`

## Top-Level Schema

```json
{
  "header": { ... },
  "model_binding": { ... },
  "contract": { ... },
  "semantic_graph": { ... },
  "neural_latent": null,
  "procedural_seed": { ... },
  "sparse_residual": { ... },
  "task_outputs": { ... },
  "semantic_checksum": { ... }
}
```

### header (required)

```json
{
  "magic": "BRK1",
  "format_version": "0.1.0",
  "profile": "BRK-Sensor",
  "created_by": "brk-local",
  "created_at": "<ISO8601 UTC>",
  "flags": {
    "lossless": false,
    "bit_exact_reconstruction": false,
    "semantic_equivalent": true
  },
  "original_size_bytes": <int or null>,
  "original_record_count": <int or null>
}
```

### model_binding (required)

```json
{
  "model_family": "BRK-Sensor-Analytic",
  "model_id": "brk-sensor-analytic",
  "version": "0.1.0",
  "decoder": "trend_daily_cycle_anomaly_injection",
  "weights_hash": null,
  "note": "Analytic local model; no neural weights."
}
```

### contract (required)

```json
{
  "mode": "brk-task",
  "domain": "agricultural_sensor",
  "lossless": false,
  "bit_exact_reconstruction": false,
  "semantic_equivalent": true,
  "tasks": ["daily_statistics", "trend_reconstruction", "anomaly_preservation"],
  "tolerances": { ... },
  "hard_constraints": ["preserve_sensor_count", "preserve_detected_anomalies"]
}
```

### semantic_checksum (required)

```json
{
  "algorithm": "sha256",
  "type": "semantic",
  "digest": "<hex string>",
  "note": "Semantic checksum over contract, semantic_graph, task_outputs, and reconstruction flags. Not a bit-exact checksum of source data."
}
```

## Required Flags (Safety Invariants)

The following invariants MUST hold in every valid `.brk` container:

1. `header.flags.lossless` MUST be `false`
2. `header.flags.bit_exact_reconstruction` MUST be `false`
3. `header.flags.semantic_equivalent` MUST be `true`
4. `contract.lossless` MUST be `false`
5. `contract.bit_exact_reconstruction` MUST be `false`
6. `contract.semantic_equivalent` MUST be `true`

Any container violating these invariants is invalid and MUST be rejected by conforming decoders.

## Semantic Checksum

The semantic checksum is computed by:
1. Constructing a payload containing: `contract`, `semantic_graph`, `task_outputs`, `flags`
2. Canonical JSON serializing this payload
3. Computing SHA-256 over the canonical bytes
4. Encoding as hex string

This is **NOT** a bit-exact checksum of the source data. It verifies the integrity of the semantic specification within the container.

## Decoder Safety Requirements

1. Decoders MUST validate the magic bytes before processing.
2. Decoders MUST validate the codec byte.
3. Decoders MUST check all safety invariants (flags, contract).
4. Decoders MUST validate the semantic checksum.
5. Decoders MUST clearly indicate in output that:
   - `reconstruction_type: "semantic_equivalent"`
   - `lossless: false`
   - `bit_exact_reconstruction: false`
6. Decoders MUST NOT claim or imply bit-exact reconstruction.

## Compatibility Policy

- Format version `0.1.0` is the initial release.
- Future versions MAY add new fields but MUST NOT remove or change the semantics of existing required fields.
- New codec bytes MAY be added in future versions.
- Decoders encountering unknown fields SHOULD ignore them.
- Decoders encountering unknown codec bytes MUST reject the file.

## Not Lossless Warning

**This format does NOT provide lossless compression.**

It does not break Shannon's theorem. It does not compress arbitrary data to a fixed size. The `.brk` container stores a semantic specification that allows approximate reconstruction within the tolerances defined by the contract. The original data CANNOT be recovered bit-for-bit from a `.brk` container.

Do not use this format for:
- Medical records requiring exact data
- Legal evidence requiring bit-exact preservation
- Cryptographic keys or secrets
- Any application where data loss is unacceptable
