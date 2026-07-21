# Legacy Artifacts

This directory contains references to historical versions of the HDAR protocol
that preceded the canonical implementation in this repository.

## Source Repository

The original development repository is at:
https://github.com/overandor/hdar-host-b-proof

It contains multiple runner versions, capsule tarballs, and run snapshots
from 2026-07-20 and 2026-07-21. These are not reproduced here because they
are superseded by the canonical implementation in `src/`.

## Historical Versions

| Directory (in source repo) | Runner size | Description |
|---|---|---|
| run-2026-07-20/ | 11,885 B | Earliest runner — hash-only, no signatures |
| run-2026-07-20-v2/ | 38,255 B | Added Ed25519 signing, external hash verification |
| run-2026-07-20-v3/ | 24,063 B | Intermediate cleanup, unused |
| _colab_build/ | 44,417 B | Latest pre-canonical runner (Colab build) |

## What Changed in Canonical

- Single protocol library (`src/hdar.py`) replaces scattered function definitions
- Single verifier (`src/verifier.py`) replaces `third_party_verifier.py`
- Single Host A sealer (`src/seal_on_host_a.py`) replaces `build_deploy_package.py`
- Single Host B runner (`src/seal_on_host_b.py`) replaces `run_on_host_b.py`
- Pinned dependency (`cryptography==44.0.1`)
- Honest claim boundary in README
- 43 tests covering all protocol operations
