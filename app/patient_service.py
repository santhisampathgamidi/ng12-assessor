"""Small patient data layer backed by `patients.json`."""

import json
from typing import Optional
from pathlib import Path
from app.config import PATIENTS_FILE


# In-memory cache loaded on first use.
_patients: dict = {}


def load_patients(filepath: Optional[Path] = None) -> None:
    """Load records from disk into the in-memory cache."""
    global _patients
    path = filepath or PATIENTS_FILE
    with open(path, "r") as f:
        records = json.load(f)
    _patients = {p["patient_id"]: p for p in records}


def get_patient(patient_id: str) -> Optional[dict]:
    """Return one patient by ID, or `None` if not found."""
    if not _patients:
        load_patients()
    return _patients.get(patient_id)


def list_patient_ids() -> list[str]:
    """Return sorted patient IDs for the UI selector."""
    if not _patients:
        load_patients()
    return sorted(_patients.keys())


def list_patients_summary() -> list[dict]:
    """Return lightweight patient records (id + name) for the frontend."""
    if not _patients:
        load_patients()
    return [
        {"patient_id": pid, "name": p["name"]}
        for pid, p in sorted(_patients.items())
    ]
