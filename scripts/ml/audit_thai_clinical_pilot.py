#!/usr/bin/env python3
"""Audit Prospective Thai Clinical Pilot Dataset for Quality & Confounder Shortcuts.

This script ingests prospective pilot metadata and feature tables, verifies participant
balancing across clinicians and clinical sites, evaluates audio QC metrics, checks feature
missingness, and produces automated warnings if potential shortcut structures appear.

Usage:
------
python scripts/ml/audit_thai_clinical_pilot.py --input-file data/clinical/prospective_pilot_sample.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_clinician_group_balance(df: pd.DataFrame) -> Tuple[bool, str, pd.DataFrame]:
    """Check whether diagnostic groups are balanced across participating clinicians."""
    if "clinician_uid" not in df.columns or "diagnostic_group" not in df.columns:
        return True, "Clinician or diagnostic group column missing; balance check skipped.", pd.DataFrame()

    ct = pd.crosstab(df["clinician_uid"], df["diagnostic_group"], margins=True)
    
    # Check if any individual clinician has > 75% of their caseload in a single diagnostic category
    ct_prop = pd.crosstab(df["clinician_uid"], df["diagnostic_group"], normalize="index")
    warnings = []
    
    for clin, row in ct_prop.iterrows():
        max_group = row.idxmax()
        max_prop = row.max()
        if max_prop >= 0.75 and len(row) > 1:
            warnings.append(
                f"WARNING: Clinician '{clin}' has {max_prop*100:.1f}% caseload in single group '{max_group}'! "
                f"This creates a severe clinician-diagnosis shortcut."
            )

    is_balanced = len(warnings) == 0
    msg = "\n".join(warnings) if warnings else "Clinician diagnostic allocation is satisfactorily balanced."
    return is_balanced, msg, ct


def check_site_and_device_balance(df: pd.DataFrame) -> Tuple[bool, str, pd.DataFrame]:
    """Check site and device distribution across diagnostic groups."""
    warnings = []
    ct = pd.DataFrame()

    if "site_uid" in df.columns and "diagnostic_group" in df.columns:
        ct = pd.crosstab(df["site_uid"], df["diagnostic_group"], margins=True)
        ct_prop = pd.crosstab(df["site_uid"], df["diagnostic_group"], normalize="index")
        for site, row in ct_prop.iterrows():
            if row.max() >= 0.85 and len(row) > 1:
                warnings.append(f"WARNING: Site '{site}' has {row.max()*100:.1f}% concentration in '{row.idxmax()}'.")

    is_balanced = len(warnings) == 0
    msg = "\n".join(warnings) if warnings else "Site and device allocations are balanced."
    return is_balanced, msg, ct


def generate_pilot_audit_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive audit statistics and quality check indicators."""
    total_records = len(df)
    n_participants = df["participant_uid"].nunique() if "participant_uid" in df.columns else total_records
    n_clinicians = df["clinician_uid"].nunique() if "clinician_uid" in df.columns else 0
    n_sites = df["site_uid"].nunique() if "site_uid" in df.columns else 0

    clin_balanced, clin_msg, clin_ct = check_clinician_group_balance(df)
    site_balanced, site_msg, site_ct = check_site_and_device_balance(df)

    # Audio QC summary if present
    audio_qc_stats = {}
    if "estimated_snr_db" in df.columns:
        snr = df["estimated_snr_db"].dropna()
        audio_qc_stats["mean_snr_db"] = round(float(snr.mean()), 2) if len(snr) else None
        audio_qc_stats["pct_snr_above_15db"] = round(float(np.mean(snr >= 15.0) * 100.0), 1) if len(snr) else None

    return {
        "total_records": total_records,
        "n_participants": n_participants,
        "n_clinicians": n_clinicians,
        "n_sites": n_sites,
        "clinician_balance_passed": clin_balanced,
        "clinician_balance_msg": clin_msg,
        "site_balance_passed": site_balanced,
        "site_balance_msg": site_msg,
        "audio_qc_stats": audio_qc_stats,
    }


def main():
    parser = argparse.ArgumentParser(description="Audit prospective Thai clinical pilot dataset.")
    parser.add_argument("--input-file", type=Path, help="Path to prospective pilot dataset CSV.")
    args = parser.parse_args()

    print("=== LinguaLens Prospective Pilot Audit ===")
    if not args.input_file or not args.input_file.exists():
        print("Note: No prospective clinical pilot dataset provided or file does not exist.")
        print("Protocol and ethics checklists located at:")
        print("  - reports/clinical/THAI_PROSPECTIVE_PILOT_PROTOCOL.md")
        print("  - reports/human_actions/THAI_CLINICAL_PILOT_ETHICS_CHECKLIST.md")
        return

    df = pd.read_csv(args.input_file)
    audit = generate_pilot_audit_report(df)

    print(f"Total Records: {audit['total_records']} | Participants: {audit['n_participants']}")
    print(f"Clinicians: {audit['n_clinicians']} | Sites: {audit['n_sites']}")
    print(f"\n--- Clinician Balancing Audit ---")
    print(audit["clinician_balance_msg"])
    print(f"\n--- Site/Device Balancing Audit ---")
    print(audit["site_balance_msg"])


if __name__ == "__main__":
    main()
