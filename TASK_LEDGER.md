# HDAR Canonical — Task Ledger

## Project Objective

Build a canonical HDAR protocol implementation with Ed25519 signed,
content-addressed transport capsules that addresses the verification
gaps identified in the artifact audit:

1. **Cryptographic authenticity (C → A)**: Ed25519 owner signatures on all capsules
2. **Full-suite reproducibility (C → A)**: Clean pytest collection, no duplicate modules
3. **Repository hygiene**: No .pyc, .DS_Store, __MACOSX in the tree

## Task Status

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| 1 | Create fixtures (input_records.jsonl, worker.py) | VERIFIED | `seal_on_host_a.py` runs successfully |
| 2 | Create Host B restore+execute+seal script | VERIFIED | `seal_on_host_b.py` produces signed E2 capsule |
| 3 | Write canonical test suite (38 tests) | VERIFIED | `38 passed in 0.12s` |
| 4 | Create project infrastructure | VERIFIED | pytest.ini, pyproject.toml, requirements.txt, .gitignore |
| 5 | Run full test suite cleanly | VERIFIED | Zero collection errors, all 38 tests pass |
| 6 | End-to-end signed capsule demo | VERIFIED | All 5 checks passed (E1 sig, E2 sig, lineage, restoration, pipeline) |
| 7 | Task ledger and hyperflow state | IN_PROGRESS | This file |
| 8 | Git init and commit | PENDING | — |

## Verification Evidence

### Test Suite
```
38 passed in 0.12s
```

Tests cover:
- Capsule seal/verify/restore integrity (12 tests)
- Ed25519 signing and hash-only fallback (11 tests)
- 5-stage pipeline determinism and edge cases (11 tests)
- Epoch lineage E1→E2→E3 chain (5 tests)

### End-to-End Demo
```
HOST A: E1 sealed, sig_valid=True, workspace destroyed
HOST B: E1 verified sig_valid=True, restored exact=True, pipeline executed, E2 sealed sig_valid=True
Lineage: E1→E2 intact, both signatures valid
```

## Architecture Decisions

1. **Single source of truth**: `src/hdar.py` is the only module defining hashing, sealing, verification, and pipeline functions. No duplicate implementations.
2. **Ed25519 with fallback**: Uses `cryptography` library when available, falls back to hash-only mode for environments without it. Signed capsules always declare their signature algorithm.
3. **Canonical JSON**: All hashes computed over `json.dumps(sort_keys=True, separators=(",",":"))` to ensure deterministic hashing.
4. **Content-addressed blocks**: Files stored as `blocks/<sha256[:2]>/<sha256>` — deduplicated by hash.
5. **No sandbox workspaces in test tree**: Tests use `tmp_path` fixtures, eliminating the duplicate `test_solve.py` collection problem from the original repository.

## Remaining Work

- [ ] Git init and first commit
- [ ] Add README.md with usage instructions
- [ ] Consider adding Host B attestation signature (separate from owner signature)
- [ ] Consider adding transparency log for capsule lineage
