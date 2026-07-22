# HDAR Protocol & SpeedOCR Ecosystem — Technical Roadmap

This document outlines the future development phases for the **HDAR Continuity Infrastructure** and the **SpeedOCR Studio** rendered-state harvesting engine.

---

## 📅 Timeline & Development Phases

### Phase 1: Hardware-Backed Key Attestation & Enclave Signing
*   **Secure Enclave Integration (macOS)**: Leverage Apple's Secure Enclave Processor (SEP) to sign SpeedOCR events and HDAR capsules with hardware-backed private keys via the `Security` framework.
*   **Cloud KMS Integration**: Build plugin drivers for AWS KMS and GCP Cloud KMS, ensuring executor private keys are never exposed in plaintext:
    $$\sigma_{\text{host}} = \operatorname{KMS.Sign}\left(\text{KeyID}, \mathcal{H}(\mathbf{M}_n)\right)$$

### Phase 2: Decentralized Registry & Sparse Merkle Indexing
*   **Global Capsule Registry**: Implement a distributed hash table (DHT) or lightweight ledger to publish capsule manifest hashes, enabling instant parent lineage lookups.
*   **Sparse Merkle Trees (SMT)**: Optimize workspace indexing for large scale directories (>100GB) by transitioning from flat maps to Sparse Merkle Trees:
    $$\mathcal{H}_{\text{root}} = \operatorname{SMT.Root}\left(\{ \operatorname{hash}(k_i) : \operatorname{hash}(v_i) \}\right)$$
    This enables $O(\log N)$ membership proofs and delta verification without downloading the entire capsule.

### Phase 3: Platform Sandbox Integrations & Attestation Drivers
*   **Sandboxed Runtimes**: Out-of-the-box drivers for E2B sandboxes, Docker containers, Kubernetes Pods, and GitHub Actions.
*   **Confidential Computing Attestations**: Verify platform integrity using hardware-attested virtual machines (e.g. AWS Nitro Enclaves, GCP Confidential VMs) by parsing AMD SEV-SNP or Intel SGX quotes.

### Phase 4: Multi-Agent Consensus & Self-Healing
*   **Consensus Reconciler**: When multiple agents execute tasks in parallel, reconcile divergent workspace states using Git-like three-way merge algorithms over Merkle tree diffs.
*   **Autonomous Rollbacks**: Auto-revert state transitions if the verifier detects security predicate failures or test breakages in successors.

---

## 📈 Metric Target Benchmarks

| Metric Target | Phase 1-2 | Phase 3-4 |
| :--- | :--- | :--- |
| **Max Workspace Size Supported** | $10\text{ GB}$ | $1\text{ TB}$ |
| **Verification Latency** | $<500\text{ ms}$ | $<50\text{ ms}$ |
| **Attestation Coverage** | OS & Python | CPU (Intel/AMD SGX) & KMS |
| **Fuzzy Line Recall** | $>98\%$ | $>99.9\%$ |
