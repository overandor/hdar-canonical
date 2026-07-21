# Archived Evidence

Verifier outputs from cross-platform HDAR proof runs performed outside this
repository. These are **snapshots** — not reproducible from the canonical
repo alone. They document that the protocol was successfully executed across
different operating systems and CPU architectures.

## E2B Sandbox (`e2b/`)

- **Host A**: macOS 26.5.2 ARM64
- **Host B**: Linux 6.8.0-1052-azure x86_64 (E2B sandbox)
- **Result**: 13/13 checks passed
- **Key finding**: Cross-platform continuation verified, Ed25519 signatures valid, pipeline output hash matches independent recompute

## GitHub Codespaces (`codespace/`)

- **Host A**: macOS 26.5.2 ARM64
- **Host B**: Linux 6.8.0-1052-azure x86_64 (GitHub Codespaces, Ubuntu 24.04)
- **Result**: 13/13 checks passed (verifier_output.json), 14/14 checks passed (verifier_on_codespace.json — includes sandbox termination confirmation)
- **Key finding**: Sandbox termination confirmed before verifier execution, all cryptographic and semantic checks passed

## ChatGPT Prototype (`chatgpt/`)

- **Host A**: macOS (local)
- **Host B**: Linux (ChatGPT code interpreter)
- **Result**: 11/12 checks passed
- **Key finding**: Lineage reference failed because E2 was from a different E1 instance. This was an early prototype run, superseded by the E2B and Codespace runs.

## Important Caveats

1. These artifacts use the **v0.1 protocol** (`hdar.transport-capsule/v0.1`),
   not the canonical v1.0 in this repository. The cryptographic primitives
   are identical; the schema version string differs.

2. The verifier used (`seed-criterion-v2`, v0.3) is a predecessor to the
   canonical `src/verifier.py` in this repo. It checked 13-14 predicates;
   the canonical verifier checks 20.

3. `overall_accept` is `false` in all runs because
   `environment_manifest_valid` was `false` (environment manifest was not
   provided in these runs). This was a known limitation of the v0.3 verifier.

4. To reproduce cross-platform proof with the canonical implementation,
   run `src/seal_on_host_a.py` on macOS, transfer the transport capsule
   tarball to a Linux machine, and run `src/seal_on_host_b.py` there.
   Then run `src/verifier.py` on any third machine.
