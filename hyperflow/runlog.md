# HDAR Canonical — Runlog

## 2026-07-21 Session

- **04:56** — Project directory `hdar-canonical` created with `src/hdar.py` and `src/seal_on_host_a.py`
- **09:00** — Created fixtures: `input_records.jsonl` (12 records), `worker.py`
- **09:01** — Created `src/seal_on_host_b.py` (restore + execute + seal successor)
- **09:02** — Created test suite: 4 test files, 38 tests total
- **09:02** — Created project infrastructure: pytest.ini, pyproject.toml, requirements.txt, .gitignore
- **09:03** — Ran `python3 -m pytest -v`: **38 passed in 0.12s** (zero collection errors)
- **09:04** — Created `demo_e2e.py` and ran end-to-end demo: **ALL CHECKS PASSED**
  - E1 sealed with Ed25519 signature: sig_valid=True
  - E1 restored on Host B: exact=True
  - Pipeline executed: 5 stages, 11 valid, 1 rejected
  - E2 sealed with Ed25519 signature: sig_valid=True
  - Lineage E1→E2: intact
- **09:05** — Created TASK_LEDGER.md and hyperflow state files
