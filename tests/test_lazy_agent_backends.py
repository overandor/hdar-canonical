import json
import zipfile
import pytest
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from hdar_core.agent.unpacker import DirectoryScanner, TarUnpacker, ZipUnpacker
from hdar_core.agent.verifier import SignatureVerifier, ChecksumVerifier, DependencyVerifier
from hdar_core.agent.generator import MockGenerator, LocalScriptGenerator
from hdar_core.agent.runner import MultiBackendLazyRunner
from hdar_core.crypto.ed25519 import generate_keypair, sign_manifest
from hdar_core.crypto.hashing import sha256_bytes


@pytest.fixture
def keys():
    return generate_keypair()


@pytest.fixture
def mock_workspace_and_manifest(tmp_path: Path, keys) -> tuple[Path, dict]:
    priv, pub = keys
    ws = tmp_path / "workspace"
    ws.mkdir()
    
    file1 = ws / "data.txt"
    file1.write_text("hello world")
    
    files_map = {
        "data.txt": sha256_bytes(b"hello world")
    }

    manifest = {
        "hdar_version": "1.2.0",
        "epoch": 1,
        "content_merkle_root": "0" * 64,
        "owner_public_key": pub,
        "timestamp": 1234567.0,
        "files": files_map
    }

    manifest_bytes = json.dumps(manifest, sort_keys=True).encode('utf-8')
    manifest_hash = sha256_bytes(manifest_bytes)
    sig = sign_manifest(priv, manifest_hash)

    capsule_data = {
        "manifest": manifest,
        "manifest_hash": manifest_hash,
        "signature": sig
    }

    # Write manifest locally inside source
    (ws / "capsule_manifest.json").write_text(json.dumps(capsule_data))
    
    return ws, capsule_data


def test_directory_scanner_pipeline_success(tmp_path: Path, mock_workspace_and_manifest):
    ws, capsule_data = mock_workspace_and_manifest
    dest_dir = tmp_path / "dest"

    unpacker = DirectoryScanner()
    verifiers = [SignatureVerifier(), ChecksumVerifier(), DependencyVerifier()]
    generator = MockGenerator()

    runner = MultiBackendLazyRunner(unpacker, verifiers, generator)
    context, report = runner.execute_pipeline(ws, dest_dir, "test prompt")

    assert report["all_passed"] is True
    assert len(report["stages"]) == 5 # unpack, verify_SignatureVerifier, verify_ChecksumVerifier, verify_DependencyVerifier, generator_execution
    assert report["stages"][-1]["status"] == "success"
    assert context["generator_output"]["text"] == "Hello from mock intelligence generator!"


def test_lazy_api_skips_on_signature_failure(tmp_path: Path, mock_workspace_and_manifest):
    ws, capsule_data = mock_workspace_and_manifest
    
    # Tamper with the signature in the source manifest
    capsule_data["signature"] = "0" * 128
    (ws / "capsule_manifest.json").write_text(json.dumps(capsule_data))

    dest_dir = tmp_path / "dest"

    unpacker = DirectoryScanner()
    verifiers = [SignatureVerifier(), ChecksumVerifier()]
    generator = MockGenerator()

    runner = MultiBackendLazyRunner(unpacker, verifiers, generator)
    context, report = runner.execute_pipeline(ws, dest_dir, "test prompt")

    assert report["all_passed"] is False
    # Verifier signature fails, remaining verifiers & generator skipped
    assert report["stages"][1]["stage"] == "verify_SignatureVerifier"
    assert report["stages"][1]["status"] == "failed"
    
    # Generator should be skipped, preventing costly API calls
    assert report["stages"][-1]["stage"] == "generator_execution"
    assert report["stages"][-1]["status"] == "skipped"


def test_zip_unpacker_pipeline(tmp_path: Path, mock_workspace_and_manifest):
    ws, capsule_data = mock_workspace_and_manifest
    zip_path = tmp_path / "capsule.zip"
    
    # Package into ZIP
    with zipfile.ZipFile(zip_path, "w") as zip_ref:
        zip_ref.write(ws / "capsule_manifest.json", arcname="capsule_manifest.json")
        zip_ref.write(ws / "data.txt", arcname="content/data.txt")

    dest_dir = tmp_path / "dest"

    unpacker = ZipUnpacker()
    verifiers = [SignatureVerifier(), ChecksumVerifier()]
    generator = MockGenerator()

    runner = MultiBackendLazyRunner(unpacker, verifiers, generator)
    context, report = runner.execute_pipeline(zip_path, dest_dir, "test prompt")

    assert report["all_passed"] is True
    assert (dest_dir / "data.txt").read_text() == "hello world"


def test_local_script_generator(tmp_path: Path, mock_workspace_and_manifest):
    ws, capsule_data = mock_workspace_and_manifest
    dest_dir = tmp_path / "dest"

    # Write a small local helper script
    helper_script = tmp_path / "helper.py"
    helper_script.write_text("import json; print(json.dumps({'status': 'ok', 'result': 42}))")

    unpacker = DirectoryScanner()
    verifiers = []
    generator = LocalScriptGenerator(script_path=helper_script)

    runner = MultiBackendLazyRunner(unpacker, verifiers, generator)
    context, report = runner.execute_pipeline(ws, dest_dir, "test prompt")

    assert report["all_passed"] is True
    assert context["generator_output"]["output"]["result"] == 42
