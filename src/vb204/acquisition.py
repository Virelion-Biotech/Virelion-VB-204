"""Integrity-checked, bounded retrieval of public Zenodo assets."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

API = "https://zenodo.org/api/records/"
USER_AGENT = "Virelion-VB204/0.3 (research reproducibility)"
DEFAULT_MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024 * 1024


def fetch_record_metadata(record_id: str) -> dict:
    record_id = str(record_id).strip()
    if not record_id.isdigit():
        raise ValueError("Zenodo record ID must be numeric")
    request = Request(API + record_id, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("files", []), list):
        raise ValueError(f"Unexpected Zenodo metadata response for record {record_id}")
    return payload


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


def _checksum_spec(value: str | None) -> tuple[str, str] | None:
    if not value or ":" not in value:
        return None
    algorithm, expected = value.split(":", 1)
    algorithm, expected = algorithm.lower().strip(), expected.lower().strip()
    if algorithm not in {"md5", "sha256"} or not expected:
        return None
    return algorithm, expected


def download_record_file(record_id: str, filename: str, output_dir: str | Path,
                         accept_license: bool = False,
                         max_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES) -> dict:
    if not accept_license:
        raise PermissionError("Review the source licence and explicitly acknowledge it before downloading.")
    if not filename or Path(filename).name != filename or filename in {".", ".."}:
        raise ValueError("filename must be an exact record filename, not a path")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    inventory = record_inventory(record_id)
    match = next((f for f in inventory["files"] if f["key"] == filename), None)
    if not match:
        raise FileNotFoundError(f"{filename!r} is not a file in Zenodo record {record_id}")
    expected_size = match.get("size")
    if isinstance(expected_size, int) and expected_size > max_bytes:
        raise ValueError(f"File size {expected_size} exceeds configured download limit {max_bytes}")
    url = str(match.get("download_url") or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "zenodo.org":
        raise ValueError("Refusing download URL that is not an HTTPS Zenodo URL")
    checksum = _checksum_spec(match.get("checksum"))
    if match.get("checksum") and checksum is None:
        raise ValueError(f"Unsupported Zenodo checksum format: {match['checksum']!r}")
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    dest = out / filename
    if dest.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {dest}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".part", dir=out)
    temp_path = Path(temp_name)
    digests = {"sha256": hashlib.sha256(), "md5": hashlib.md5()}
    total = 0
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=120) as response, os.fdopen(fd, "wb") as target:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"Download exceeded configured limit of {max_bytes} bytes")
                for digest in digests.values():
                    digest.update(chunk)
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        if isinstance(expected_size, int) and total != expected_size:
            raise ValueError(f"Downloaded size mismatch: expected {expected_size} bytes, received {total}")
        if checksum:
            algorithm, expected = checksum
            actual = digests[algorithm].hexdigest()
            if actual != expected:
                raise ValueError(f"Checksum mismatch ({algorithm}): expected {expected}, received {actual}")
        os.replace(temp_path, dest)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        temp_path.unlink(missing_ok=True)
        raise
    return {
        "record_id": str(record_id), "filename": filename, "path": str(dest),
        "bytes_downloaded": total, "sha256": digests["sha256"].hexdigest(),
        "record_checksum": match.get("checksum"), "checksum_verified": bool(checksum),
        "record_size_verified": isinstance(expected_size, int), "source_url": url,
        "doi": inventory.get("doi"), "license": inventory.get("license"),
        "license_review_acknowledged": True
    }
