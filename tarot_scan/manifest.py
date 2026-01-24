"""JSONL manifest read/write utilities."""

import json
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel

from tarot_scan.models import CardCropMeta, ClassRecord, ManifestRecord, ScanMeta


def read_manifest(path: Path) -> list[dict]:
    """Read all records from a JSONL manifest file.

    Args:
        path: Path to manifest.jsonl

    Returns:
        List of record dictionaries
    """
    if not path.exists():
        return []

    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def iter_manifest(path: Path) -> Iterator[dict]:
    """Iterate over records in a manifest file.

    Args:
        path: Path to manifest.jsonl

    Yields:
        Record dictionaries
    """
    if not path.exists():
        return

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def append_record(path: Path, record: BaseModel) -> None:
    """Append a record to the manifest file.

    Args:
        path: Path to manifest.jsonl
        record: Pydantic model to append
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(record.model_dump_json() + "\n")


def parse_record(data: dict) -> ManifestRecord:
    """Parse a manifest record dict into the appropriate model.

    Args:
        data: Record dictionary with 'type' field

    Returns:
        Parsed Pydantic model

    Raises:
        ValueError: Unknown record type
    """
    record_type = data.get("type")
    if record_type == "scan":
        return ScanMeta.model_validate(data)
    elif record_type == "crop":
        return CardCropMeta.model_validate(data)
    elif record_type == "class":
        return ClassRecord.model_validate(data)
    else:
        raise ValueError(f"Unknown record type: {record_type}")


def get_scans(path: Path) -> list[ScanMeta]:
    """Get all scan records from manifest."""
    return [
        ScanMeta.model_validate(r) for r in read_manifest(path) if r.get("type") == "scan"
    ]


def get_crops(path: Path) -> list[CardCropMeta]:
    """Get all crop records from manifest."""
    return [
        CardCropMeta.model_validate(r) for r in read_manifest(path) if r.get("type") == "crop"
    ]


def get_classifications(path: Path) -> list[ClassRecord]:
    """Get all classification records from manifest."""
    return [
        ClassRecord.model_validate(r) for r in read_manifest(path) if r.get("type") == "class"
    ]


def get_pending_crops(path: Path) -> list[CardCropMeta]:
    """Get crops that haven't been classified yet."""
    records = read_manifest(path)

    # Build set of classified crop IDs
    classified_ids = {r["crop_id"] for r in records if r.get("type") == "class"}

    # Return crops not in classified set
    return [
        CardCropMeta.model_validate(r)
        for r in records
        if r.get("type") == "crop" and r["crop_id"] not in classified_ids
    ]


def get_next_scan_id(path: Path) -> str:
    """Get the next scan ID (scan_NNNN format)."""
    scans = get_scans(path)
    if not scans:
        return "scan_0001"
    max_num = max(int(s.scan_id.split("_")[1]) for s in scans)
    return f"scan_{max_num + 1:04d}"


def get_next_crop_id(path: Path) -> str:
    """Get the next crop ID (card_NNNN format)."""
    crops = get_crops(path)
    if not crops:
        return "card_0001"
    max_num = max(int(c.crop_id.split("_")[1]) for c in crops)
    return f"card_{max_num + 1:04d}"
