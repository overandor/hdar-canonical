import json
import zipfile
import tarfile
from pathlib import Path


class BaseUnpacker:
    """Interface for unpacking various capsule formats."""
    def unpack(self, source_path: Path, dest_dir: Path) -> dict:
        raise NotImplementedError("Subclasses must implement unpack")


class TarUnpacker(BaseUnpacker):
    """Unpacks gzip-compressed tarballs (.tar.gz)."""
    def unpack(self, source_path: Path, dest_dir: Path) -> dict:
        if not source_path.exists():
            raise FileNotFoundError(f"Tarball not found: {source_path}")
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        capsule_data = {}

        with tarfile.open(source_path, "r:gz") as tar:
            # Try loading manifest first
            meta_member = None
            for member in tar.getmembers():
                if member.name == "capsule_manifest.json":
                    meta_member = member
                    break
            
            if not meta_member:
                raise ValueError("Invalid tar capsule: missing capsule_manifest.json")
            
            meta_file = tar.extractfile(meta_member)
            if meta_file:
                capsule_data = json.loads(meta_file.read().decode('utf-8'))

            # Extract content files
            for member in tar.getmembers():
                if member.name.startswith("content/"):
                    rel_path = member.name.replace("content/", "")
                    out_path = dest_dir / rel_path
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    f_data = tar.extractfile(member)
                    if f_data:
                        out_path.write_bytes(f_data.read())

        return capsule_data


class ZipUnpacker(BaseUnpacker):
    """Unpacks zip archives (.zip)."""
    def unpack(self, source_path: Path, dest_dir: Path) -> dict:
        if not source_path.exists():
            raise FileNotFoundError(f"Zip archive not found: {source_path}")
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        capsule_data = {}

        with zipfile.ZipFile(source_path, "r") as zip_ref:
            # Check for manifest
            if "capsule_manifest.json" not in zip_ref.namelist():
                raise ValueError("Invalid zip capsule: missing capsule_manifest.json")
            
            manifest_bytes = zip_ref.read("capsule_manifest.json")
            capsule_data = json.loads(manifest_bytes.decode('utf-8'))

            # Extract content files
            for name in zip_ref.namelist():
                if name.startswith("content/"):
                    rel_path = name.replace("content/", "")
                    out_path = dest_dir / rel_path
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(zip_ref.read(name))

        return capsule_data


class DirectoryScanner(BaseUnpacker):
    """Simulates unpacking by reading/scanning a raw uncompressed directory."""
    def unpack(self, source_path: Path, dest_dir: Path) -> dict:
        if not source_path.exists() or not source_path.is_dir():
            raise FileNotFoundError(f"Source directory not found: {source_path}")
        
        manifest_path = source_path / "capsule_manifest.json"
        if not manifest_path.exists():
            raise ValueError("Invalid directory capsule: missing capsule_manifest.json")

        with manifest_path.open("r", encoding="utf-8") as f:
            capsule_data = json.load(f)

        # Copy files to destination if different, else just verify they exist
        if source_path.resolve() != dest_dir.resolve():
            import shutil
            dest_dir.mkdir(parents=True, exist_ok=True)
            for file_path in source_path.rglob("*"):
                if file_path.is_file() and file_path.name != "capsule_manifest.json":
                    rel_path = file_path.relative_to(source_path)
                    if rel_path.parts[0] == "content":
                        # Skip content prefix wrapper if present, otherwise handle structure
                        rel_path = Path(*rel_path.parts[1:])
                    out_path = dest_dir / rel_path
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, out_path)

        return capsule_data
