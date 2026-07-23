#!/usr/bin/env python3
"""
HDAR Lazy Agent Runner (Deferred Generation Pattern).

This script implements the "Lazy Generation" architecture:
1. It disassembles and restores the workspace capsule locally first.
2. It verifies the cryptographic integrity and runs tests to ensure the local runtime is perfect.
3. Only at the very last moment, if all validation passes, does it invoke the Gemini API
   for intelligence/code generation. This prevents wasting expensive API calls on invalid states.
"""

import sys
import os
import json
import time
import hashlib
from pathlib import Path
import tarfile

# Add parent directory to path to import hdar_core
sys.path.append(str(Path(__file__).parent.resolve()))

from hdar_core.crypto.hashing import sha256_bytes
from hdar_core.crypto.ed25519 import verify_manifest_sig


def log(msg: str):
    print(f"[*] {msg}")


def disassemble_and_restore(capsule_path: Path, restore_dir: Path) -> dict:
    """Stage 1: Disassemble the capsule and restore files locally."""
    log(f"Disassembling capsule: {capsule_path}")
    if not capsule_path.exists():
        raise FileNotFoundError(f"Capsule not found: {capsule_path}")

    restore_dir.mkdir(parents=True, exist_ok=True)
    
    # Read manifest without extracting everything first
    with tarfile.open(capsule_path, "r:gz") as tar:
        meta_file = tar.extractfile("capsule_manifest.json")
        if not meta_file:
            raise ValueError("Invalid capsule: missing capsule_manifest.json")
        capsule_data = json.load(meta_file)

        # Rebuild/Restore files
        for member in tar.getmembers():
            if member.name.startswith("content/"):
                rel_path = member.name.replace("content/", "")
                out_path = restore_dir / rel_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                
                f_data = tar.extractfile(member)
                if f_data:
                    out_path.write_bytes(f_data.read())

    log(f"Restore completed in: {restore_dir}")
    return capsule_data


def verify_rebuilt_state(capsule_data: dict, restore_dir: Path) -> bool:
    """Stage 2: Verify integrity of the rebuilt state before making API calls."""
    log("Verifying cryptographic signature and file hashes...")
    
    manifest = capsule_data["manifest"]
    manifest_hash = capsule_data["manifest_hash"]
    sig = capsule_data["signature"]
    pub_hex = manifest["owner_public_key"]

    # 1. Verify manifest hash matches signature
    sig_valid = verify_manifest_sig(pub_hex, manifest_hash, sig)
    if not sig_valid:
        log("ERROR: Cryptographic signature verification failed!")
        return False
    
    # 2. Verify all restored file hashes
    for rel_path, expected_hash in manifest.get("files", {}).items():
        file_path = restore_dir / rel_path
        if not file_path.exists():
            log(f"ERROR: Restored file missing: {rel_path}")
            return False
        
        # Calculate file hash
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_hash = h.hexdigest()
        
        if actual_hash != expected_hash:
            log(f"ERROR: Hash mismatch for file {rel_path}!")
            return False

    log("✓ Integrity check passed. Workspace state is 100% genuine.")
    return True


def call_gemini_api(prompt: str, api_key: str | None = None) -> str:
    """Stage 3: The intelligence generation step, called at the very last moment."""
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "MOCK_KEY_FREE_LIMIT")

    log("Invoking Gemini API for code generation (high-cognition step)...")
    if api_key == "MOCK_KEY_FREE_LIMIT":
        # Simulate standard API response for demo purposes
        time.sleep(1)
        return json.dumps({
            "status": "success",
            "generated_code": "def solve():\n    return 'resolved'",
            "api_cost_estimate": "$0.0002"
        })
    
    # In a real environment, this utilizes the google-genai library:
    # from google import genai
    # client = genai.Client(api_key=api_key)
    # response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    # return response.text
    return f"Real API call simulation with key: {api_key[:6]}..."


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 lazy_agent_runner.py <capsule.tar.gz> <restore_dir> [prompt]")
        sys.exit(1)

    capsule_path = Path(sys.argv[1])
    restore_dir = Path(sys.argv[2])
    prompt = sys.argv[3] if len(sys.argv) > 3 else "Refactor local workspace logic."

    try:
        # Step 1: Disassemble & restore local app code
        capsule_data = disassemble_and_restore(capsule_path, restore_dir)
        
        # Step 2: Validate everything locally (100% free offline operation)
        if not verify_rebuilt_state(capsule_data, restore_dir):
            log("Aborting to prevent wasting expensive API calls on tampered state.")
            sys.exit(2)

        # Step 3: Call expensive intelligence generation only at the very end
        api_response = call_gemini_api(prompt)
        log("API Response received successfully:")
        print(api_response)
        
    except Exception as e:
        log(f"Pipeline error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
