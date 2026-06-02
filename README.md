<div align="center">

# 🚀 BRK — Breakthrough Container

**Semantic / Task-Oriented Reconstruction Container**

> **BRK does not break Shannon's theorem.**  
> **BRK is not a universal lossless compressor.**  
> **BRK stores a contract-bound semantic specification for acceptable reconstruction.**

**BRK は Shannon の定理を破りません。**  
**BRK は任意データを完全可逆圧縮するものではありません。**  
**BRK は明確な契約に基づいた意味的再構成仕様を保存します。**

![Version](https://img.shields.io/badge/version-0.1-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## ✨ What is BRK?

**BRK (Breakthrough Container)** は、**.brk** 拡張子の **意味指向・タスク指向再構成コンテナ** です。

従来の圧縮形式とは異なり、**ビット完全な復元ではなく**、**明確な契約（contract）に基づいた意味的・統計的に十分な再構成**を目的としています。

### BRK が適している場面
- 1GBを超える巨大なCSV/Time-seriesデータを扱うとき
- 個々のデータポイントより、**傾向・統計・異常値**が重要なとき
- 完全な復元ではなく「意味的に十分」な再現で良いとき
- ローカル環境だけで高速処理したいとき

---

## ❌ BRK はこれではありません

| ❌ 該当しないこと | 説明 |
|------------------|------|
| Universal Lossless Compressor | 任意データを完全可逆圧縮しません |
| Shannon's Theorem Breaker | 情報理論を破りません |
| Bit-exact Archival | 医療・法律・暗号データには使用不可 |
| Cloud / AI API依存 | 完全ローカル動作 |

---

## ✅ BRK ができること

- **統計的・意味的忠実性**の保持（傾向、日周期、異常値）
- **ストリーミング処理**（1GB超のCSVもメモリに全載せ不要）
- **1KB目標**の極小コンテナ（契約ベース）
- **明確な安全フラグ**（Lossless = false を常に明示）
- **完全ローカル**（クラウド不要）

---

## 🎯 BRK-Sensor Profile v0.1

農業・IoTセンサー時系列データに最適化された最初のプロファイル。

### 処理フロー
1. **Pass 1**: Welford法で統計量を計算（平均、標準偏差、傾き、日平均など）
2. **Pass 2**: 異常値検出（z-score）
3. **保存**: 意味仕様のみを `.brk` に圧縮
4. **再構成**: 傾向 + 日周期 + 異常注入 で意味的に等価な時系列を生成

---

## 🚀 クイックスタート

```bash
# インストール
pip install -e .

# 圧縮
brk compress-sensor data/sensor.csv output.brk

# 確認
brk inspect output.brk

# 再構成
brk decompress-sensor output.brk reconstructed.csv
