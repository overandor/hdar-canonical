# HDAR Protocol & Rendered-State Harvesting: Technical Whitepaper

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](pyproject.toml)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/overandor/hdar-canonical)
[![GitHub Pages](https://img.shields.io/badge/Docs-GitHub%20Pages-blue.svg)](https://overandor.github.io/hdar-canonical/)

> **Abstract**: Autonomous software agents operate across isolated cloud sandboxes, local desktops, and ephemeral container runtimes. Establishing verifiable state continuity, provenance, and zero-loss rendered-state harvesting requires mathematical bounds on sampling rates, cryptographic signature chains, and content-addressed storage. This paper formalizes the **HDAR Canonical Protocol** and the **Trajectory-Based Rendered-State Harvesting Engine**.

---

## 1. Mathematical Formalism & Error Metrics

### 1.1 Character Error Rate (CER) and Word Error Rate (WER)
Standard optical character recognition (OCR) models compute transcription fidelity via normalized Levenshtein edit distance:

$$\text{CER} = \frac{S + D + I}{N} = \frac{\sum_{i=1}^{M} \operatorname{lev}(g_i, r_i)}{\sum_{i=1}^{M} |g_i|}$$

where $S$ is substitutions, $D$ is deletions, $I$ is insertions, $g_i$ is the ground-truth string, and $r_i$ is the recognized string.

### 1.2 Sampling Rate & Capture Miss Probability ($P_{\text{miss}}$)
When sampling screen video frames at effective frequency $f_{\text{effective}}$, text elements visible for duration $T$ experience an idealized sampling miss probability:

$$P_{\text{miss}}(T, f_{\text{effective}}) = \max\left(0, 1 - f_{\text{effective}} \cdot T\right)$$

At a sampling rate of $f_{\text{effective}} = 6\text{ Hz}$ ($T_{\text{sample}} = 166.7\text{ ms}$):

| Text Visible Duration ($T$) | Nominal Sampling Miss Probability ($P_{\text{miss}}$) |
| :--- | :--- |
| $40\text{ ms}$ | $76\%$ |
| $80\text{ ms}$ | $52\%$ |
| $120\text{ ms}$ | $28\%$ |
| $166.7\text{ ms}$ | $0\%$ |

### 1.3 Harvest Recall ($\mathcal{R}_{\text{harvest}}$)
For rendered-state harvesters, the primary figure of merit is **Harvest Recall**, defined as the fraction of unique ground-truth lines captured at least once across dynamic scroll operations:

$$\mathcal{R}_{\text{harvest}} = \frac{|\mathcal{L}_{\text{ground\_truth}} \cap \mathcal{L}_{\text{harvested}}|}{|\mathcal{L}_{\text{ground\_truth}}|}$$

---

## 2. Cryptographic Capsule Provenance & Merkle Lineage

### 2.1 Content-Addressed Workspace Hashing
Workspace files $\{f_1, f_2, \dots, f_K\}$ are mapped into content-addressed SHA-256 blocks:

$$\mathcal{H}_{\text{block}}(f_i) = \operatorname{SHA256}(\operatorname{Bytes}(f_i))$$

The overall workspace Merkle root $\mathcal{H}_{\text{root}}$ is computed deterministically over sorted relative paths:

$$\mathcal{H}_{\text{root}} = \operatorname{SHA256}\left( \text{CanonicalJSON}\left( \{ \text{rel\_path}_i : \mathcal{H}_{\text{block}}(f_i) \}_{i=1}^K \right) \right)$$

### 2.2 Ed25519 Signature Verification
Each capsule manifest $\mathbf{M}_n$ is signed by the workspace owner using Ed25519 public key cryptography:

$$\sigma_n = \operatorname{Ed25519.Sign}\left( sk_{\text{owner}}, \operatorname{SHA256}(\operatorname{CanonicalJSON}(\mathbf{M}_n)) \right)$$

$$\mathcal{V}_{\text{Ed25519}}(pk_{\text{owner}}, \sigma_n, \mathcal{H}(\mathbf{M}_n)) \in \{\text{True}, \text{False}\}$$

### 2.3 Cryptographic Lineage Chain ($\mathbf{E}_n$)
An Epoch transition chain is formally defined as an ordered sequence of verified tuples:

$$\mathbf{E}_n = \left\langle \mathcal{H}_n, \mathcal{H}_{n-1}, \mathcal{H}_{\text{root}, n}, pk_{\text{owner}}, \sigma_{\text{owner}, n}, \text{Attest}_{\text{host}_n} \right\rangle$$

where $\mathcal{H}_0 = \mathbf{0}^{256}$ and $\mathcal{H}_{n-1}$ is the parent manifest hash, guaranteeing immutable state provenance across multi-cloud execution environments:

$$\mathbf{E}_1 \xrightarrow{\sigma_1} \mathbf{E}_2 \xrightarrow{\sigma_2} \dots \xrightarrow{\sigma_N} \mathbf{E}_N$$

---

## 3. Trajectory-Based Adaptive Frame Selection Architecture

```text
60 FPS Video Stream (ScreenCaptureKit)
        │
        ▼
   Visual Change & Motion Velocity Detection
        │
        ▼
   Candidate Frame Buffer Window
        │
        ▼
   Stabilization Detection (Deceleration Point)
        │
        ▼
   High-DPI Upscaling Engine (2.5x Lanczos Scale)
        │
        ▼
   Vision OCR (minimumTextHeight = 0.001)
        │
        ▼
   Multi-Pass Temporal Word Consensus
```

---

## 4. Quick Start & CLI Execution

### 4.1 Install via Pip
```bash
pip install -r requirements.txt
```

### 4.2 Run End-to-End Cryptographic Proof Demo
```bash
python3 demo_e2e.py --out /tmp/hdar_demo
```

### 4.3 Run Pytest Verification Suite
```bash
python3 -m pytest -v
```

### 4.4 Enterprise CLI Tooling
```bash
# Seal workspace into signed capsule
python3 src/hdar_cli.py seal --workspace . --output /tmp/capsule.hdar.tar.gz --epoch 1

# Audit capsule security predicates
python3 src/hdar_cli.py verify --capsule /tmp/capsule.hdar.tar.gz
```

---

## 5. License
Licensed under the [MIT License](LICENSE).
