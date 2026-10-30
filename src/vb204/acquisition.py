"""Explicit, traceable retrieval of public Zenodo model assets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://zenodo.org/api/records/"

def fetch_record_metadata(record_id: str) -> dict:
    if not str(record_id).isdigit():
        raise ValueError("Zenodo record ID must be numeric")
    request = Request(API + record_id, headers={"User-Agent": "Virelion-VB204/0.2 (research reproducibility)"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def record_inventory(record_id: str) -> dict:
    record = fetch_record_metadata(record_id)
    return {
        "record_id": str(record.get("id", record_id)), "doi": record.get("doi"),
        "title": record.get("metadata", {}).get("title"),
        "publication_date": record.get("metadata", {}).get("publication_date"),
        "license": record.get("metadata", {}).get("license"),
        "files": [{
            "key": f.get("key"), "size": f.get("size"), "checksum": f.get("checksum"),
            "download_url": f.get("links", {}).get("self")
        } for f in record.get("files", [])],
        "metadata_url": API + record_id, "downloaded": False
    }

def download_record_file(record_id: str, filename: str, output_dir: str | Path, accept_license: bool = False) -> dict:
    if not accept_license:
        raise PermissionError("Review source license and invoke with accept_license=True to explicitly acknowledge the download.")
    if not filename or Path(filename).name != filename or filename in {".", ".."}:
        raise ValueError("filename must be an exact record filename, not a path")
    inventory = record_inventory(record_id)
    match = next((f for f in inventory["files"] if f["key"] == filename), None)
    if not match:
        raise FileNotFoundError(f"{filename!r} is not a file in Zenodo record {record_id}")
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    dest = out / filename
    if dest.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {dest}")
    request = Request(match["download_url"], headers={"User-Agent": "Virelion-VB204/0.2 (research reproducibility)"})
    digest = hashlib.sha256()
    total = 0
    with urlopen(request, timeout=120) as response, dest.open("wb") as target:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            target.write(chunk)
            digest.update(chunk)
            total += len(chunk)
    return {
        "record_id": record_id, "filename": filename, "path": str(dest),
        "bytes_downloaded": total, "sha256": digest.hexdigest(),
        "record_checksum": match.get("checksum"), "source_url": match["download_url"],
        "doi": inventory.get("doi"), "license": inventory.get("license"),
        "license_review_acknowledged": True
    }
