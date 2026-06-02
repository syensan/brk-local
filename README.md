<div align="center">

# 🚀 BRK — Breakthrough Container

**Semantic • Task-Oriented • Reconstruction Container**

> **BRK does not break Shannon's theorem.**  
> **BRK is not a universal lossless compressor.**  
> **BRK stores a contract-bound semantic specification for acceptable reconstruction.**

![Version](https://img.shields.io/badge/version-0.1-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## ✨ What is BRK?

**BRK (Breakthrough Container)** is a **semantic and task-oriented reconstruction container** with the `.brk` file extension.

Unlike traditional compression formats that aim for bit-exact reconstruction, **BRK stores a contract-bound semantic specification** that enables high-quality *approximate* reconstruction within clearly defined tolerances.

### Ideal Use Cases
- Extremely large datasets (1GB+ CSV files)
- Time-series data where trends, statistics, and anomalies matter more than exact values
- Scenarios where dramatic size reduction is needed with acceptable semantic fidelity
- Memory-efficient streaming processing
- Local-first environments (no cloud, no external APIs)

---

## ❌ What BRK Is NOT

| ❌ Not | Description |
|-------|-------------|
| Universal Lossless Compressor | Cannot compress arbitrary data losslessly |
| Shannon's Theorem Breaker | Does not violate information theory |
| Bit-Exact Archival Format | Not suitable for medical, legal, financial, or cryptographic data |
| Cloud-Dependent | Runs 100% locally |

---

## ✅ What BRK IS

- Semantic reconstruction container with explicit contracts
- Preserves statistical properties, trends, daily cycles, and anomalies
- Streaming two-pass processor for massive files
- Extremely compact (target: ~1KB)
- Always explicitly states it is **not lossless**

---

## 🎯 BRK-Sensor Profile v0.1

The first official profile, optimized for **agricultural and IoT sensor time-series data** (CSV/JSON).

### Processing Pipeline
1. **Pass 1** — Stream CSV and compute statistics (mean, std, min, max, slope, hourly patterns) using Welford’s online algorithm
2. **Pass 2** — Detect anomalies using z-score
3. **Store** — Save only the semantic specification in a compact `.brk` container
4. **Reconstruct** — Generate statistically equivalent data using trend + daily cycle + anomaly injection

---

## 🚀 Quick Start

```bash
# Install
pip install -e .

# Compress
brk compress-sensor data/sample_sensor.csv output.brk

# Inspect
brk inspect output.brk
