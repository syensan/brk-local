# Contributing to BRK

Thank you for your interest in contributing to BRK — Breakthrough Container!

## Important Principles

**BRK is NOT a universal lossless compressor.** Any contribution must maintain this principle:

- `lossless` must always be `false`
- `bit_exact_reconstruction` must always be `false`
- `semantic_equivalent` must always be `true`
- No claim of breaking Shannon's theorem
- No claim of arbitrary data compression to fixed size

## Development Setup

```bash
git clone git clonegit clone https://github.com/syensan/brk-local.git

cd brk-local
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -e .
pip install pytest
```

## Running Tests

```bash
pytest -v
```

All 47+ tests must pass before submitting a PR.

## Code Style

- Python 3.11+ with type hints
- `dataclasses` for structured data
- `argparse` for CLI (no heavy dependencies)
- Streaming / two-pass for large files (no full in-memory loads)
- Canonical JSON for all serialization
- UTC timestamps everywhere
- Functions should be small and focused

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Add tests for your changes
4. Ensure all tests pass (`pytest -v`)
5. Commit with descriptive messages
6. Open a pull request

## Reporting Issues

- Use GitHub Issues
- Include Python version, OS, and steps to reproduce
- For .brk file issues, include the output of `brk inspect` and `brk verify`

## Safety Review

All PRs are reviewed for safety invariant compliance. Changes that:
- Set `lossless=true` anywhere
- Remove safety flag validation
- Claim bit-exact reconstruction
- Imply Shannon's theorem is broken

...will be rejected.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
