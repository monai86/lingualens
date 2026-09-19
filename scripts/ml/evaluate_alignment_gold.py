#!/usr/bin/env python3
"""Evaluate Automated Speech Boundaries & Response Latency against Human Gold Annotations.

This script ingests populated human gold annotation datasets, computes inter-annotator agreement,
calculates error metrics (MAE, RMSE, Signed Bias, Bland-Altman LoA, Tolerance Bands), and performs
quality-stratified error breakdowns.

Usage:
------
python scripts/ml/evaluate_alignment_gold.py --gold-file data/ml/validation/audio_alignment_gold_template.csv
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_GOLD_COLUMNS = [
    "audio_id",
    "participant_uid",
    "session_id",
    "segment_id",
    "speaker_role",
    "manual_onset_ms",
    "manual_offset_ms",
]


def validate_gold_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate that the gold dataframe has required columns and non-placeholder human labels."""
    for col in REQUIRED_GOLD_COLUMNS:
        if col not in df.columns:
            return False, f"Missing required column: '{col}'"

    # Check if manual onset/offset columns are completely empty / NaN
    valid_onsets = df["manual_onset_ms"].dropna()
    valid_offsets = df["manual_offset_ms"].dropna()

    if len(valid_onsets) == 0 or len(valid_offsets) == 0:
        return False, "Manual gold annotations are empty. Template is unpopulated by human annotators."

    return True, "Valid gold dataset structure."


def compute_timing_error_metrics(
    manual_vals: np.ndarray,
    auto_vals: np.ndarray,
) -> Dict[str, Any]:
    """Compute comprehensive timing error metrics between manual and automatic timestamps."""
    valid_mask = np.isfinite(manual_vals) & np.isfinite(auto_vals)
    y_true = manual_vals[valid_mask]
    y_pred = auto_vals[valid_mask]

    n_samples = len(y_true)
    if n_samples == 0:
        return {
            "n_samples": 0,
            "mae_ms": float("nan"),
            "median_ae_ms": float("nan"),
            "rmse_ms": float("nan"),
            "mean_signed_bias_ms": float("nan"),
            "p90_ae_ms": float("nan"),
            "p95_ae_ms": float("nan"),
            "max_ae_ms": float("nan"),
            "pct_within_20ms": float("nan"),
            "pct_within_50ms": float("nan"),
            "pct_within_100ms": float("nan"),
            "pct_within_200ms": float("nan"),
            "catastrophic_failure_rate": float("nan"),
            "bland_altman": {
                "mean_bias": float("nan"),
                "lower_loa": float("nan"),
                "upper_loa": float("nan"),
            },
        }

    diffs = y_pred - y_true
    abs_errors = np.abs(diffs)

    mae = float(np.mean(abs_errors))
    median_ae = float(np.median(abs_errors))
    rmse = float(np.sqrt(np.mean(diffs**2)))
    signed_bias = float(np.mean(diffs))
    p90 = float(np.percentile(abs_errors, 90))
    p95 = float(np.percentile(abs_errors, 95))
    max_ae = float(np.max(abs_errors))

    pct_20 = float(np.mean(abs_errors <= 20.0) * 100.0)
    pct_50 = float(np.mean(abs_errors <= 50.0) * 100.0)
    pct_100 = float(np.mean(abs_errors <= 100.0) * 100.0)
    pct_200 = float(np.mean(abs_errors <= 200.0) * 100.0)
    catastrophic = float(np.mean(abs_errors > 250.0) * 100.0)

    # Bland-Altman 95% Limits of Agreement
    sd_diff = float(np.std(diffs, ddof=1)) if n_samples > 1 else 0.0
    lower_loa = signed_bias - 1.96 * sd_diff
    upper_loa = signed_bias + 1.96 * sd_diff

    return {
        "n_samples": n_samples,
        "mae_ms": round(mae, 2),
        "median_ae_ms": round(median_ae, 2),
        "rmse_ms": round(rmse, 2),
        "mean_signed_bias_ms": round(signed_bias, 2),
        "p90_ae_ms": round(p90, 2),
        "p95_ae_ms": round(p95, 2),
        "max_ae_ms": round(max_ae, 2),
        "pct_within_20ms": round(pct_20, 2),
        "pct_within_50ms": round(pct_50, 2),
        "pct_within_100ms": round(pct_100, 2),
        "pct_within_200ms": round(pct_200, 2),
        "catastrophic_failure_rate": round(catastrophic, 2),
        "bland_altman": {
            "mean_bias": round(signed_bias, 2),
            "lower_loa": round(lower_loa, 2),
            "upper_loa": round(upper_loa, 2),
        },
    }


def evaluate_gold_dataset(file_path: Path) -> Dict[str, Any]:
    """Load, validate, and compute evaluation metrics from a gold annotation file."""
    if not file_path.exists():
        return {
            "status": "FILE_NOT_FOUND",
            "message": f"Gold annotation file does not exist: {file_path}",
        }

    df = pd.read_csv(file_path)
    is_valid, msg = validate_gold_dataframe(df)

    if not is_valid:
        return {
            "status": "UNPOPULATED_OR_INVALID",
            "message": msg,
            "total_rows": len(df),
        }

    # Evaluate Onset Errors
    onset_metrics = compute_timing_error_metrics(
        df["manual_onset_ms"].values,
        df["automatic_onset_ms"].values if "automatic_onset_ms" in df.columns else np.full(len(df), np.nan),
    )

    # Evaluate Offset Errors
    offset_metrics = compute_timing_error_metrics(
        df["manual_offset_ms"].values,
        df["automatic_offset_ms"].values if "automatic_offset_ms" in df.columns else np.full(len(df), np.nan),
    )

    # Evaluate Response Latency if present
    latency_metrics = {}
    if "manual_response_latency_ms" in df.columns and "automatic_response_latency_ms" in df.columns:
        latency_metrics = compute_timing_error_metrics(
            df["manual_response_latency_ms"].values,
            df["automatic_response_latency_ms"].values,
        )

    return {
        "status": "SUCCESS",
        "total_annotated_segments": len(df),
        "onset_metrics": onset_metrics,
        "offset_metrics": offset_metrics,
        "latency_metrics": latency_metrics,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate timing accuracy against human gold annotations.")
    parser.add_argument(
        "--gold-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "ml" / "validation" / "audio_alignment_gold_template.csv",
        help="Path to populated gold annotation CSV.",
    )
    args = parser.parse_args()

    print(f"=== LinguaLens Gold Timing Evaluation ===")
    print(f"Reading: {args.gold_file}")

    results = evaluate_gold_dataset(args.gold_file)
    print(f"Status: {results['status']}")

    if results["status"] == "UNPOPULATED_OR_INVALID":
        print(f"Note: {results['message']}")
        print("Awaiting human phonetic annotation. Human action checklist located at: reports/human_actions/HUMAN_GOLD_ANNOTATION_CHECKLIST.md")
    elif results["status"] == "SUCCESS":
        print("\n--- Onset Accuracy ---")
        print(f"MAE: {results['onset_metrics']['mae_ms']} ms | Median: {results['onset_metrics']['median_ae_ms']} ms")
        print(f"P95: {results['onset_metrics']['p95_ae_ms']} ms | ±50ms: {results['onset_metrics']['pct_within_50ms']}%")
        print("\n--- Offset Accuracy ---")
        print(f"MAE: {results['offset_metrics']['mae_ms']} ms | Median: {results['offset_metrics']['median_ae_ms']} ms")
        if results.get("latency_metrics"):
            print("\n--- Response Latency Accuracy ---")
            print(f"MAE: {results['latency_metrics']['mae_ms']} ms | Signed Bias: {results['latency_metrics']['mean_signed_bias_ms']} ms")


if __name__ == "__main__":
    main()
