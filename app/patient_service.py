"""
Patient Data Service — simulates a database (BigQuery) retrieval layer.
Loads patient records from patients.json and exposes a lookup function
that the Gemini agent can call as a tool.
"""

import json
from typing import Optional
from pathlib import Path
from app.config import PATIENTS_FILE


# ---------------------------------------------------------------------------
# In-memory patient store (loaded once at startup)
# ---------------------------------------------------------------------------
_patients: dict = {}


def load_patients(filepath: Optional[Path] = None) -> None:
    """Load patient records from JSON into the in-memory store."""
    global _patients
    path = filepath or PATIENTS_FILE
    with open(path, "r") as f:
        records = json.load(f)
    _patients = {p["patient_id"]: p for p in records}


def get_patient(patient_id: str) -> Optional[dict]:
    """
    Retrieve a single patient record by ID.
    Returns None if the patient is not found.
    This is the function exposed as an agent tool.
    """
    if not _patients:
        load_patients()
    return _patients.get(patient_id)


def list_patient_ids() -> list[str]:
    """Return all available patient IDs (for the UI dropdown)."""
    if not _patients:
        load_patients()
    return sorted(_patients.keys())


def list_patients_summary() -> list[dict]:
    """Return a summary list of all patients (id + name) for the frontend."""
    if not _patients:
        load_patients()
    return [
        {"patient_id": pid, "name": p["name"]}
        for pid, p in sorted(_patients.items())
    ]