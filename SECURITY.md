<!-- BRK is NOT a universal lossless compressor. -->
<!-- BRK does not break Shannon's theorem. -->

# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in BRK, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email: security@brk-local.dev (or open a private security advisory on GitHub)
3. Include: description, steps to reproduce, affected versions, potential impact

## Known Limitations (NOT vulnerabilities)

The following are **by design** and not security issues:

- BRK containers are **NOT** lossless — original data cannot be recovered
- Semantic checksums verify specification integrity, **NOT** source data fidelity
- Reconstructed data is approximate, **NOT** bit-exact
- Do not use BRK for medical records, legal evidence, or cryptographic data

## Safety Invariants

These must never be bypassed:

- `header.flags.lossless = false`
- `header.flags.bit_exact_reconstruction = false`
- `header.flags.semantic_equivalent = true`
- `contract.lossless = false`
- `contract.semantic_equivalent = true`

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Active development |

## Threat Model

- **Local execution only**: BRK runs on the user's machine
- **No network calls**: No data is transmitted externally
- **No encryption**: .brk files are not encrypted; protect files at the OS level
- **No authentication**: Anyone with read access can decompress a .brk file
