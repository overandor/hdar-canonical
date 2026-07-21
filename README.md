# HDAR Canonical

Signed, content-addressed transport capsules for host-to-host workspace continuation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (43 tests, ~1 second)
python3 -m pytest -v

# Run end-to-end demo: Host A seals → Host B restores + executes → Verifier C checks
python3 demo_e2e.py --out /tmp/hdar_demo
```

One command. Three phases. The demo runs Host A, Host B, and the independent
verifier as separate subprocesses, producing:

- `host_a/` — E1 capsule, build report, owner public key, transport tarball
- `host_b/` — E2 capsule, Host B report, transport tarball
- `verifier_report.json` — independent verifier output (20 checks)

To run the verifier manually against existing artifacts:

```bash
python3 src/verifier.py \
  --host-a-report /tmp/hdar_demo/host_a/host_a_build_report.json \
  --host-b-report /tmp/hdar_demo/host_b/host_b_report.json \
  --e1-capsule /tmp/hdar_demo/host_a/capsule_epoch_1 \
  --e2-capsule /tmp/hdar_demo/host_b/capsule_epoch_2 \
  --owner-public-key /tmp/hdar_demo/host_a/owner_public_key.txt \
  --out /tmp/hdar_demo/verifier_report.json
```

## Architecture

```
src/hdar.py            — Canonical protocol library (hashing, sealing, verification, pipeline)
src/seal_on_host_a.py  — Host A: create workspace, seal Epoch 1, destroy workspace
src/seal_on_host_b.py  — Host B: restore E1, execute pipeline, seal Epoch 2
src/verifier.py        — Independent verifier: 20 checks against all artifacts
fixtures/              — Demo workspace fixtures (input data, worker script)
tests/                 — 43 tests: integrity, crypto, pipeline, lineage, verifier
demo_e2e.py            — One-command end-to-end proof
```

## Key Properties

- **Ed25519 signed capsules**: Every capsule carries an owner signature over the manifest hash
- **Content-addressed blocks**: Files stored as `blocks/<sha256[:2]>/<sha256>` — deduplicated
- **Cryptographic lineage**: E2 manifest references E1 manifest hash, forming a chain
- **Deterministic pipeline**: 5-stage task (parse, filter, aggregate, classify, report) with hash-chained stages
- **Independent verification**: Third-party verifier checks signatures, hashes, lineage, and semantic correctness without trusting any other component
- **Hash-only fallback**: Works without `cryptography` library (degrades to hash-only mode)
- **Pinned dependency**: `cryptography==44.0.1` for reproducibility

## What This Proves

When run on a **single machine** (local demo mode), this repository demonstrates:

1. Ed25519 signing and verification of capsule manifests works correctly
2. Content-addressed workspace hashing produces deterministic, verifiable results
3. Workspace restoration from a sealed capsule is byte-exact (root hash matches)
4. The 5-stage deterministic pipeline produces a reproducible output hash
5. Cryptographic lineage (E1 to E2) is correctly established and verifiable
6. An independent verifier validates the full chain (20 checks) without trusting either host
7. Host A workspace destruction is confirmed after sealing

## What This Does NOT Prove (Local Demo)

- **Cross-platform portability**: Both Host A and Host B run on the same OS in local demo mode. The platform separation check is a warning, not a hard failure. Real cross-platform proof requires running Host B on a different OS (Linux, E2B, Colab, Codespaces).
- **Operator separation**: The same person runs both hosts. There is no independent operator verifying the chain.
- **Byte-identical capsule reproduction**: Capsule manifests contain timestamps, so byte-identical reproduction across builds is not possible. This is acceptable for unique authenticated state but means the capsule itself is not deterministic across builds.
- **Adversarial host evaluation**: Host B is cooperative. The protocol does not yet test what happens when Host B attempts to cheat.
- **Multi-hop lineage**: Only E1 to E2 is demonstrated. The protocol supports longer chains but they are not tested here.
- **Production-grade key management**: Owner keys are generated in-memory per demo run. No key rotation, revocation, or HSM backing is implemented.

## Cross-Platform Evidence

Real cross-platform runs were performed outside this repository using:

- **E2B sandbox** (Linux x86_64) — 15/15 verifier checks passed
- **GitHub Codespaces** (Ubuntu 24.04 x86_64) — 13/13 verifier checks passed
- **Google Colab** (Linux x86_64) — Host B execution confirmed

Evidence artifacts from these runs are in `archived_evidence/`. These are
snapshots, not reproducible from this repository alone. To reproduce
cross-platform proof, run `demo_e2e.py` with Host B on a remote Linux machine
using the transport capsule tarball from Host A.

## Verification Results

```
Tests:     43 passed in 0.97s (zero collection errors)
E2E demo:  19/20 checks passed (1 expected warning: same-platform local demo)
Verifier:  all_passed=true (platform separation is a warning, not a hard failure)
```

## License

This software is provided as-is for evaluation purposes. No warranty is expressed or implied.
