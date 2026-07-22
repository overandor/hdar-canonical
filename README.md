# HDAR Continuity Infrastructure

Verifiable state continuity and provenance infrastructure for autonomous software agents and computational workspaces moving between machines, clouds, and execution sandboxes.

## The Problem
As autonomous agents transition from passive suggestions to active execution (modifying codebases, running tests, deploying services), they move across distinct sandbox boundaries and providers. Organizations cannot reliably prove:
* Which agent or host produced a state change.
* Whether the workspace was tampered with during transport.
* Whether execution occurred in a compliant environment.
* Whether the successor state advanced correctly and passed required tests.

## The Solution: HDAR Gateway
HDAR solves the trust gap by packaging workspace state, continuation points, and cryptographic provenance into verifiable **Agent Capsules** that chain across execution hosts.

```
[Host A (Mac)] -> Epoch 1 Capsule -> [Host B (GitHub Sandbox)] -> Epoch 2 Capsule -> [Host C (Cloud Alloydb Sandbox)] -> Epoch 3 Capsule
                                                                                             |
                                                                                    [Independent Verifiers]
                                                                                      - python verifier
                                                                                      - Node.js verifier
```

---

## Quick Start (Seed Demonstration)

Get the complete 3-epoch proof, tampering audit, and multi-language verification running with these commands:

### 1. Install Dependencies (Optional)
Runs in zero-dependency, hash-only fallback mode if `cryptography` is missing, but Ed25519 signatures are fully validated if installed:
```bash
pip install -r requirements.txt
```

### 2. Run the 3-Epoch E2E Coding Workload Demo
Executes Host A (Initialization) $\rightarrow$ Host B (Autonomous coding agent fixing a division bug and running tests) $\rightarrow$ Host C (Verification summary & task list completion) $\rightarrow$ Python Verifier:
```bash
python3 hdar_portable.py demo --out /tmp/hdar_seed_demo
```

### 3. Run the Fail-Safe Tampering/Security Audit
Demonstrates real-time defense against content block tampering, manifest metadata modification, and key spoofing attacks:
```bash
python3 hdar_portable.py demo-failure --out /tmp/hdar_seed_failure
```

### 4. Run the Independent Node.js Verifier
Validate the entire 3-epoch sequence using a completely separate Node.js implementation:
```bash
node verifier.js \
  --host-a-report /tmp/hdar_seed_demo/host_a/host_a_build_report.json \
  --host-b-report /tmp/hdar_seed_demo/host_b/host_b_report.json \
  --host-c-report /tmp/hdar_seed_demo/host_c/host_c_report.json \
  --e1-capsule /tmp/hdar_seed_demo/host_a/capsule_epoch_1 \
  --e2-capsule /tmp/hdar_seed_demo/host_b/capsule_epoch_2 \
  --e3-capsule /tmp/hdar_seed_demo/host_c/capsule_epoch_3 \
  --owner-public-key /tmp/hdar_seed_demo/host_a/owner_public_key.txt \
  --out /tmp/hdar_seed_demo/node_verifier_report.json
```

---

## What this repo proves

HDAR demonstrates that an owner‑signed, content‑addressed workspace can be restored and deterministically advanced within multiple separately provisioned runtime configurations, producing cryptographically linked successor epochs and byte‑identical pipeline output. Host A, capsule integrity, lineage, and computation are independently verifiable; Host B runtime identity and provider provenance remain unauthenticated.

This phrasing aligns the headline claim with the evidence chain, acknowledging the current limitation around Host B authentication while highlighting the strongest technical results: frozen E1, deterministic output, and independent Rust verification.

---

## Seed-Ready Architecture & Moat

### 1. Agent Capsule
A content-addressed, signed workspace snapshot containing files, manifest, receipt, ownership keys, and lineage pointers.

### 2. Transition Verifier
Checks 20 security predicates, verifying that:
* Lineage is cryptographically intact ($E_1 \rightarrow E_2 \rightarrow E_3$).
* State advanced correctly (verified that the division bug in `main_app.py` is resolved in $E_2$ and $E_3$).
* Receipts and content blocks match their SHA-256 hashes exactly.
* Both the owner (authorization) and executors (host identity keys) signed the transitions.

### 3. Host Executor Attestations
Each runtime environment creates its own signature, embedding platform/provider attestations (e.g. GitHub Actions, secure sandboxes).

---

## Running Legacy Core Tests
To execute the legacy 43 pytest unit cases:
```bash
python3 -m pytest -v
```

## License
Licensed under evaluation terms.
