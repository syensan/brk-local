# BRK — Breakthrough Container

> **BRK does not break Shannon's theorem.**
> **BRK is not a universal lossless compressor.**
> **BRK stores a contract-bound semantic specification for acceptable reconstruction.**

> **BRK は Shannon の定理を破るものではありません。**
> **BRK は任意データを完全可逆圧縮する形式ではありません。**
> **BRK は明示された契約に基づき、意味的・タスク的に十分な再構成仕様を保存する形式です。**

---

## What is BRK?

BRK (Breakthrough Container) is a **semantic / task-oriented reconstruction container format** with the `.brk` file extension. Unlike traditional compression formats that aim for bit-exact decompression, BRK stores a **contract-bound semantic specification** that allows approximate reconstruction of data within defined tolerances.

BRK is designed for scenarios where:
- The original data is too large to store or transmit in full
- Statistical properties, trends, and anomalies are more important than individual data points
- A clearly defined reconstruction contract is acceptable
- You need to process 1GB+ CSV files without loading them entirely into memory

### What BRK Is NOT

- ❌ A universal lossless compressor
- ❌ A format that breaks Shannon's theorem
- ❌ A way to compress arbitrary data to 1KB losslessly
- ❌ A replacement for bit-exact archival storage
- ❌ Suitable for medical records, legal evidence, cryptographic keys, or any data where loss is unacceptable

### What BRK IS

- ✅ A semantic reconstruction container with explicit contracts
- ✅ A format that preserves statistical properties, trends, daily cycles, and anomalies
- ✅ A streaming/two-pass processor that handles 1GB+ CSV files
- ✅ A local/on-premises tool — no cloud, no serverless, no external AI APIs
- ✅ A format that clearly and repeatedly states it is NOT lossless

---

## BRK-Sensor Profile v0.1

The first profile is **BRK-Sensor**, designed for agricultural and IoT sensor time-series data (CSV/JSON). It:

1. **Pass 1**: Streams through CSV, computing per-sensor/per-metric statistics (mean, std, min, max, first, last, slope, hourly means) using Welford's online algorithm
2. **Pass 2**: Re-streams the CSV, detecting z-score anomalies against Pass 1 statistics
3. **Stores**: The semantic specification (statistics, trends, anomalies) in a `.brk` container
4. **Reconstructs**: Generates a semantic-equivalent time series using trend + daily cycle + anomaly injection

---

## Installation

```bash
# Clone or download the repository
cd brk-local

# Install in development mode
pip install -e .

# Or just run directly
python -m brk --help
```

### Requirements

- Python 3.11+
- Standard library (no external dependencies required for core functionality)
- pytest (for running tests)

---

## CLI Usage

### Help

```bash
brk --help
python -m brk --help
```

### Compress a Sensor CSV

```bash
brk compress-sensor examples/sample_sensor.csv output.brk
```

Options:
- `--contract <path>`: Path to custom contract JSON
- `--budget <bytes>`: Target budget in bytes (default: 1024)
- `--max-anomalies <n>`: Maximum anomalies to preserve (default: 32)
- `--anomaly-z <threshold>`: Z-score threshold for anomaly detection (default: 3.0)
- `--strict-budget`: Fail if output exceeds budget after reduction
- `--quiet`: Suppress informational output
- `--json-report <path>`: Save compression report as JSON

Output:
```
BRK-Sensor compression complete.
Output: output.brk
Output size: 842 bytes
Target budget: 1024 bytes
Within budget: true
Lossless: false
Bit-exact reconstruction: false
Semantic equivalent: true
```

### Inspect a .brk Container

```bash
brk inspect output.brk
```

Shows header, model binding, contract, sensor count, metric count, duration, anomaly count, and file size. Explicitly states that the container does NOT provide bit-exact reconstruction.

### Verify a .brk Container

```bash
brk verify output.brk
```

Validates:
- Container structure
- Safety flags (lossless=false, bit_exact_reconstruction=false, semantic_equivalent=true)
- Contract invariants
- Semantic checksum

### Decompress (Reconstruct) a CSV

```bash
brk decompress-sensor output.brk reconstructed.csv --step-minutes 60
```

Options:
- `--step-minutes <n>`: Time step for reconstruction in minutes (default: 60)
- `--metadata-json <path>`: Save reconstruction metadata as JSON

Output:
```
BRK-Sensor reconstruction complete.
Output: reconstructed.csv
Reconstruction type: semantic_equivalent
Lossless: false
Bit-exact reconstruction: false
Semantic checksum valid: true
```

---

## Sample CSV

```csv
ts,sensor_id,temperature,humidity,soil_moisture
2026-01-01T00:00:00Z,field-01,20.1,61.2,33.4
2026-01-01T01:00:00Z,field-01,19.8,63.0,33.1
2026-01-01T02:00:00Z,field-01,50.0,62.8,12.0
2026-01-01T03:00:00Z,field-01,20.4,60.9,33.6
2026-01-01T04:00:00Z,field-01,20.2,61.1,33.2
2026-01-01T00:00:00Z,field-02,18.2,70.1,40.2
2026-01-01T01:00:00Z,field-02,18.1,70.5,40.0
2026-01-01T02:00:00Z,field-02,18.3,70.0,39.9
2026-01-01T03:00:00Z,field-02,18.2,69.8,40.1
```

Note: The `50.0` temperature at `field-01` hour 2 is an anomaly.

---

## How Reconstruction Works

The reconstruction algorithm (`trend_daily_cycle_anomaly_injection`) generates approximate values:

1. **Base trend**: `first_value + slope_per_second × elapsed_seconds`
2. **Daily cycle**: `hourly_mean[current_hour] - overall_mean` (if hourly data available)
3. **Anomaly injection**: If an anomaly is recorded for this timestamp, inject the anomaly value

This produces an approximate time series that preserves the overall statistical properties, trends, and detected anomalies — but it is **NOT** the original data.

---

## 1KB Target Budget

The default target budget is 1024 bytes, but this is a **target**, not a guarantee. The actual size depends on:

- Number of sensors
- Number of metrics
- Number of anomalies
- Complexity of hourly patterns
- Precision of floating-point values

If the output exceeds the budget in strict mode, progressive reduction is applied:
- Level 0: Full detail
- Level 1: Reduce hourly_mean precision
- Level 2: Remove hourly_mean
- Level 3: Halve anomaly count
- Level 4: Quarter anomaly count
- Level 5: Budget failure (error)

In non-strict mode (default), the file is created even if it exceeds the budget, with a warning displayed.

---

## When BRK Works Well

- ✅ Agricultural sensor data with regular intervals and clear daily patterns
- ✅ IoT environmental monitoring with periodic readings
- ✅ Time-series data where statistical properties matter more than individual points
- ✅ Data with detectable anomalies that must be preserved
- ✅ Scenarios needing dramatic size reduction with acceptable approximation

## When BRK Does NOT Work Well

- ❌ Data requiring bit-exact preservation (financial transactions, medical records)
- ❌ Legal evidence or regulatory compliance data
- ❌ Cryptographic keys, secrets, or authentication tokens
- ❌ Data with no discernible patterns or trends (pure noise)
- ❌ Very high-dimensional data with hundreds of metrics
- ❌ Scenarios where any data loss is unacceptable

---

## Architecture

```
.brk file = MAGIC + CODEC_BYTE + zlib(canonical_json(container))

container = {
    header,              // format metadata and safety flags
    model_binding,       // decoder specification
    contract,            // reconstruction contract and tolerances
    semantic_graph,      // statistical summary, trends, hourly patterns
    neural_latent,       // null for v0.1 (no neural model)
    procedural_seed,     // deterministic reconstruction seed
    sparse_residual,     // anomaly points
    task_outputs,        // summary counts
    semantic_checksum    // integrity verification (NOT bit-exact)
}
```

### Safety Invariants (always enforced)

- `header.flags.lossless` = `false`
- `header.flags.bit_exact_reconstruction` = `false`
- `header.flags.semantic_equivalent` = `true`
- `contract.lossless` = `false`
- `contract.bit_exact_reconstruction` = `false`
- `contract.semantic_equivalent` = `true`
- All CLI output clearly states `Lossless: false`

---

## Running Tests

```bash
cd brk-local
pytest -v
```

---

## Project Structure

```
brk-local/
├─ pyproject.toml
├─ README.md
├─ LICENSE
├─ .gitignore
├─ .github/
│  └─ workflows/
│     └─ ci.yml              # GitHub Actions CI (3 OS × 3 Python versions)
├─ docs/
│  ├─ index.html          # Web docs with IP-based auto-translation (14 languages)
│  ├─ llms.txt            # LLM-optimized project summary
│  ├─ llms-full.txt       # Full LLM-optimized documentation
│  ├─ sitemap.xml         # SEO sitemap
│  └─ robots.txt          # SEO robots
├─ mime/
│  ├─ brk.xml               # Linux shared-mime-info (MIME type + magic bytes)
│  ├─ brk-inspect.desktop   # Linux .desktop file (right-click Inspect)
│  ├─ brk-association.reg   # Windows registry file association
│  ├─ install-association.ps1  # Windows PowerShell installer
│  ├─ install-association.sh   # Linux Bash installer
│  ├─ install-association-macos.sh  # macOS installer
│  └─ BRKType.plist         # macOS UTType declaration
├─ specs/
│  ├─ BRK-v0.1.md          # Container format specification
│  └─ BRK-Sensor-v0.1.md   # Sensor profile specification
├─ brk/
│  ├─ __init__.py
│  ├─ __main__.py           # python -m brk entry point
│  ├─ cli.py                # CLI commands
│  ├─ constants.py          # Format constants
│  ├─ container.py          # Read/write .brk files
│  ├─ checksum.py           # Semantic checksum
│  ├─ contracts.py          # Contract definitions and validation
│  ├─ errors.py             # Exception hierarchy
│  ├─ sensor/
│  │  ├─ csv_reader.py      # Streaming CSV reader
│  │  ├─ stats.py           # Welford statistics, anomaly detection
│  │  ├─ compressor.py      # Two-pass compression
│  │  ├─ decompressor.py    # Semantic reconstruction
│  │  ├─ verifier.py        # Container verification
│  │  └─ schema.py          # Data structure definitions
│  └─ util/
│     ├─ json.py            # Canonical JSON serialization
│     ├─ time.py            # Timestamp utilities
│     └─ size.py            # Size formatting
├─ examples/
│  ├─ sample_sensor.csv
│  ├─ sample_contract.json
│  └─ expected_readme.md
└─ tests/
   ├─ test_container.py
   ├─ test_checksum.py
   ├─ test_sensor_stats.py
   ├─ test_sensor_roundtrip.py
   └─ test_cli.py
```

---

## File Association: Make .brk a Real Extension

BRK registers `.brk` as a recognized file extension with MIME type `application/vnd.brk` on all major platforms. The `mime/` directory contains platform-specific installers:

### Linux (freedesktop.org)

```bash
# System-wide (requires sudo)
sudo bash mime/install-association.sh

# User-local (no sudo needed)
bash mime/install-association.sh --user

# Uninstall
bash mime/install-association.sh --uninstall [--user]
```

After installation:
- `.brk` files are recognized as `application/vnd.brk`
- Magic bytes `BRK1\n` detected automatically
- Double-click → `brk inspect` in terminal
- Right-click → Verify / Reconstruct CSV options
- `file output.brk` shows: `output.brk: application/vnd.brk`

### Windows

```powershell
# Method 1: Registry file (double-click to install)
# Open mime/brk-association.reg and confirm import

# Method 2: PowerShell (recommended)
powershell -ExecutionPolicy Bypass -File mime/install-association.ps1

# Uninstall
powershell -ExecutionPolicy Bypass -File mime/install-association.ps1 -Uninstall
```

After installation:
- `.brk` files show "BRK Breakthrough Container" type in Explorer
- Double-click → `brk inspect` in terminal
- Right-click → Verify / Reconstruct CSV options
- Content type: `application/vnd.brk`

### macOS

```bash
# Install with Homebrew duti (recommended)
brew install duti
bash mime/install-association-macos.sh

# Or manually via BRKType.plist
# Copy mime/BRKType.plist to ~/Library/Preferences/
```

### Verify MIME Registration

```bash
# Linux
file --mime-type output.brk
# → output.brk: application/vnd.brk

xdg-mime query filetype output.brk
# → application/vnd.brk

# macOS
duti -x brk
```

---

## Ethical and Safety Considerations

- **Do not use BRK for data where loss is unacceptable**: Medical records, legal evidence, financial audit trails, cryptographic keys, authentication tokens, or any data where even minor data loss could cause harm.
- **BRK is explicit about its limitations**: Every layer of the system — CLI output, container flags, contracts, checksums, README, and specs — clearly states that reconstruction is NOT lossless.
- **Semantic checksums are NOT bit-exact checksums**: They verify the integrity of the semantic specification, not the original data. Do not use them as evidence of data fidelity.
- **Reconstruction is approximate**: The reconstructed data will not match the original data point-by-point. It preserves statistical properties and trends within the contract's tolerances.
- **1KB target is not a guarantee**: The actual compressed size depends on data complexity. Complex data will exceed the budget.
- **No cloud dependencies**: BRK runs entirely locally. No data is sent to external services.

---

## SEO & LLMO

### For Search Engines

- **Structured data**: JSON-LD schema (`SoftwareApplication`, `TechArticle`) embedded in `docs/index.html`
- **Open Graph / Twitter Card**: Full meta tags for social sharing
- **Sitemap**: `docs/sitemap.xml`
- **Robots**: `docs/robots.txt`
- **hreflang**: 14-language alternate links for multilingual SEO
- **Canonical URL**: Set in HTML head

### For LLMs (Large Language Model Optimization)

- **llms.txt**: `docs/llms.txt` — concise project summary for LLM crawlers
- **llms-full.txt**: `docs/llms-full.txt` — complete specification and API documentation
- **Machine-readable metadata**: JSON-LD `TechArticle` schema with proficiency level and topic
- **Clear safety invariants**: All non-lossless guarantees machine-parseable

### Multilingual Documentation

The `docs/index.html` page provides:
- **14 languages**: English, 日本語, 中文, 한국어, Français, Deutsch, Español, Português, Italiano, Русский, العربية, ไทย, Tiếng Việt, Bahasa Indonesia
- **IP-based auto-detection**: Uses ipapi.co geolocation to detect visitor's language
- **URL parameter override**: `?lang=ja` for explicit language selection
- **Browser fallback**: Falls back to `navigator.language` if IP detection fails

---

## License

MIT License. See [LICENSE](LICENSE) for details.
#   b r k - l o c a l  
 