# HDAR Canonical

Signed, content-addressed transport capsules for host-to-host workspace continuation.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (43 tests, ~1 second)
python3 -m pytest -v

# Run end-to-end demo (Host A seals → Host B restores, executes, seals successor)
python3 demo_e2e.py --out /tmp/hdar_demo

# Run independent verifier against demo output
python3 src/verifier.py \
  --host-a-report /tmp/hdar_demo/host_a/host_a_build_report.json \
  --host-b-report /tmp/hdar_demo/host_b/host_b_report.json \
  --e1-capsule /tmp/hdar_demo/host_a/capsule_epoch_1 \
  --e2-capsule /tmp/hdar_demo/host_b/capsule_epoch_2 \
  --owner-public-key /tmp/hdar_demo/host_a/owner_public_key.txt
```

## Architecture

```
src/hdar.py            — Canonical protocol library (hashing, sealing, verification, pipeline)
src/seal_on_host_a.py  — Host A: create workspace, seal Epoch 1, destroy workspace
src/seal_on_host_b.py  — Host B: restore E1, execute pipeline, seal Epoch 2
src/verifier.py        — Independent verifier: 20 checks against all artifacts
fixtures/              — Demo workspace fixtures
tests/                 — 43 tests: integrity, crypto, pipeline, lineage, verifier
```

## Key Properties

- **Ed25519 signed capsules**: Every capsule carries an owner signature over the manifest hash
- **Content-addressed blocks**: Files stored as `blocks/<sha256[:2]>/<sha256>` — deduplicated
- **Cryptographic lineage**: E2 manifest references E1 manifest hash, forming a chain
- **Deterministic pipeline**: 5-stage task (parse → filter → aggregate → classify → report) with hash-chained stages
- **Independent verification**: Third-party verifier checks signatures, hashes, lineage, and semantic correctness without trusting any other component
- **Hash-only fallback**: Works without `cryptography` library (degrades to hash-only mode)

## Verification Results

```
Tests:     43 passed in 1.00s (zero collection errors)
E2E demo:  ALL CHECKS PASSED (E1 sig, E2 sig, lineage, restoration, pipeline)
Verifier:  19/20 checks passed (1 expected warning: same-platform local demo)
```
