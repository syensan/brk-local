---
name: Bug Report
about: Report a bug in BRK
title: "[BUG] "
labels: bug
assignees: ''
---

## Bug Description

A clear description of what the bug is.

## Steps to Reproduce

1. ...
2. ...
3. ...

## Expected Behavior

What you expected to happen.

## Actual Behavior

What actually happened.

## Environment

- OS: [e.g. Windows 11, Ubuntu 22.04, macOS 14]
- Python version: [e.g. 3.12.0]
- BRK version: [e.g. 0.1.0]
- Installation method: [pip install -e . / pip install brk-local]

## BRK Inspect Output (if applicable)

```
Paste the output of: brk inspect <file.brk>
```

## BRK Verify Output (if applicable)

```
Paste the output of: brk verify <file.brk>
```

## Additional Context

Any other context about the problem.

---

**Reminder**: BRK is NOT a universal lossless compressor. Reconstruction is always approximate (semantic_equivalent=true). If your issue is about reconstructed data not matching the original exactly, this is by design.
