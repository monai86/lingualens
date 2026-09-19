"""Unit tests for Phase 4 Human Gold Evaluation, Thai Pilot Audit, and Tone-Aware Specs."""

import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ml.evaluate_alignment_gold import (
    compute_timing_error_metrics,
    evaluate_gold_dataset,
    validate_gold_dataframe,
)
from scripts.ml.audit_thai_clinical_pilot import (
    check_clinician_group_balance,
    generate_pilot_audit_report,
)


def test_gold_schema_validation_unpopulated_template():
    """Verify that unpopulated template is detected without raising exceptions or computing fake numbers."""
    template_path = PROJECT_ROOT / "data" / "ml" / "validation" / "audio_alignment_gold_template.csv"
    assert template_path.exists(), "Template CSV must exist."

    res = evaluate_gold_dataset(template_path)
    assert res["status"] == "UNPOPULATED_OR_INVALID"
    assert "empty" in res["message"] or "unpopulated" in res["message"].lower()


def test_compute_timing_error_metrics_synthetic():
    """Test timing error metric computations including negative overlaps, MAE, RMSE, and Bland-Altman."""
    manual = np.array([500.0, 600.0, -150.0, 800.0, 1000.0])  # Note -150 is valid overlap
    auto = np.array([520.0, 580.0, -140.0, 830.0, 990.0])

    metrics = compute_timing_error_metrics(manual, auto)
    assert metrics["n_samples"] == 5
    # diffs: +20, -20, +10, +30, -10 -> abs: 20, 20, 10, 30, 10 -> mean = 18.0
    assert metrics["mae_ms"] == 18.0
    assert metrics["median_ae_ms"] == 20.0
    assert metrics["mean_signed_bias_ms"] == 6.0  # (20-20+10+30-10)/5 = 6.0
    assert metrics["pct_within_50ms"] == 100.0
    assert metrics["catastrophic_failure_rate"] == 0.0
    assert "mean_bias" in metrics["bland_altman"]
    assert "lower_loa" in metrics["bland_altman"]
    assert "upper_loa" in metrics["bland_altman"]


def test_timing_error_metrics_empty():
    """Verify that empty inputs return NaN gracefully without crashing."""
    manual = np.array([])
    auto = np.array([])
    metrics = compute_timing_error_metrics(manual, auto)
    assert metrics["n_samples"] == 0
    assert math.isnan(metrics["mae_ms"])


def test_clinician_shortcut_detection_triggers_warning():
    """Verify that severe clinician-diagnosis confounding is flagged by the audit script."""
    # Clinician A sees 90% ASD, Clinician B sees 90% TD
    data = {
        "participant_uid": [f"p_{i}" for i in range(20)],
        "clinician_uid": ["clin_A"] * 10 + ["clin_B"] * 10,
        "diagnostic_group": ["ASD"] * 9 + ["TD"] * 1 + ["ASD"] * 1 + ["TD"] * 9,
    }
    df = pd.DataFrame(data)
    is_balanced, msg, _ = check_clinician_group_balance(df)

    assert not is_balanced, "Auditor should detect imbalanced clinician caseload."
    assert "WARNING" in msg
    assert "clin_A" in msg


def test_clinician_shortcut_detection_passes_on_balanced():
    """Verify that balanced caseload passes audit."""
    data = {
        "participant_uid": [f"p_{i}" for i in range(18)],
        "clinician_uid": ["clin_A"] * 6 + ["clin_B"] * 6 + ["clin_C"] * 6,
        "diagnostic_group": ["ASD", "DD", "TD"] * 6,
    }
    df = pd.DataFrame(data)
    is_balanced, msg, _ = check_clinician_group_balance(df)

    assert is_balanced
    assert "satisfactorily balanced" in msg


def test_speaker_centered_f0_formula():
    """Verify mathematical calculation of speaker-centered semitones."""
    # If child median F0 is 250 Hz, a pitch frame of 500 Hz (one octave higher) is +12 semitones
    child_median_hz = 250.0
    frame_hz = 500.0
    st_centered = 12.0 * math.log2(frame_hz / child_median_hz)
    assert math.isclose(st_centered, 12.0, rel_tol=1e-5)

    # A pitch frame of 250 Hz is 0 semitones relative to child median
    st_same = 12.0 * math.log2(child_median_hz / child_median_hz)
    assert math.isclose(st_same, 0.0, abs_tol=1e-5)
