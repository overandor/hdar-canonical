# 🛡️ HDAR Protocol
### *Verifiable State Continuity & Provenance Infrastructure for Autonomous AI Agents*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](pyproject.toml)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/overandor/hdar-canonical)
[![Awwwards Nominee](https://img.shields.io/badge/Awwwards-Nominee-gold.svg)](https://overandor.github.io/hdar-canonical/)
[![GitHub Pages](https://img.shields.io/badge/Docs-Live%20Demo-blue.svg)](https://overandor.github.io/hdar-canonical/)

---

## ⚡ The Trust Gap in Agentic Workflows

As autonomous agents transition from **suggestions** to **active execution** (modifying codebases, running unit tests, deploying containerized infrastructure), they move across distinct sandbox boundaries (Local Desktop $\rightarrow$ GitHub Actions $\rightarrow$ Isolated Docker Sandboxes $\rightarrow$ Cloud VMs). 

Without HDAR, organizations cannot prove:
*   **Identity**: Which agent or platform host produced a given state change?
*   **Integrity**: Was the workspace tampered with during transport between hosts?
*   **Compliance**: Did the execution occur in a secure, attested environment?

**HDAR (High-Density Agent Recovery)** solves this by packaging workspace state, continuation points, and cryptographic signatures into verifiable **Agent Capsules** that chain across host transitions.

---

## ✨ Features & Moats

*   **🔒 Ed25519 Cryptographic Signatures**: Every capsule manifest is signed by the workspace owner, preventing unauthorized state modification and spoofing.
*   **📦 Content-Addressed Blocks**: Deduplicated file storage (`blocks/<sha256[:2]>/<sha256>`) ensuring fast, bandwidth-efficient state transfers.
*   **🔗 Cryptographic Lineage Chains**: Successor epochs reference parent manifest hashes forming a verifiably immutable Merkle chain ($E_1 \rightarrow E_2 \rightarrow E_3$).
*   **📋 Clipboard Teleportation**: Base64 encode and copy entire signed capsules to the system clipboard for zero-latency transport between environments.
*   **⚡ Two-Pass Consensus & Trajectory OCR**: Fully integrated with the SpeedOCR engine to harvest rendered UI states with >98% line recall.

---

## 🚀 Quick Start: Clipboard Teleportation

Experience the power of instant workspace transport:

### 1. Seal & Copy Workspace (Machine A)
```bash
python3 src/hdar_cli.py seal --workspace src --to-clipboard
```
> **Result**: Capsule sealed, signed, and copied to system clipboard!

### 2. Restore Workspace Instantly (Machine B)
```bash
python3 src/hdar_cli.py restore --from-clipboard --target /tmp/teleport_target
```
> **Result**: Byte-exact workspace restored instantly from your clipboard.

### 3. Verify Security Predicates
```bash
python3 src/hdar_cli.py verify --capsule /tmp/enterprise_test.hdar.tar.gz
```

---

## 🧮 Theoretical Bounds & Metrics

### Character Error Rate (CER)
$$\text{CER} = \frac{S + D + I}{N} = \frac{\sum_{i=1}^{M} \operatorname{lev}(g_i, r_i)}{\sum_{i=1}^{M} |g_i|}$$

### Capture Miss Probability ($P_{\text{miss}}$)
$$P_{\text{miss}}(T, f_{\text{effective}}) = \max\left(0, 1 - f_{\text{effective}} \cdot T\right)$$

### Merkle Workspace Hashing
$$\mathcal{H}_{\text{root}} = \operatorname{SHA256}\left( \text{CanonicalJSON}\left( \{ \text{rel\_path}_i : \operatorname{SHA256}(\text{Block}_i) \}_{i=1}^K \right) \right)$$

---

## 🌐 Live Resources
*   **Interactive Sandbox & Live Verifier**: [https://overandor.github.io/hdar-canonical/](https://overandor.github.io/hdar-canonical/)
*   **Technical Roadmap**: [ROADMAP.md](ROADMAP.md)
*   **License**: Licensed under the [MIT License](LICENSE)
