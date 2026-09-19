"""Unit and integration tests for the ML pipeline, data integrity, and leakage prevention."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import GroupKFold

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ml.train_baselines import apply_resampling, compute_metrics
from src.feature_schema import FEATURES


DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_PATH = DATA_DIR / "ml" / "participant_registry.csv"
PARQUET_PATH = DATA_DIR / "ml" / "canonical_features.parquet"
CSV_PATH = DATA_DIR / "ml" / "canonical_features.csv"
XLSX_PATH = DATA_DIR / "ml" / "canonical_features.xlsx"


def test_participant_registry_exists_and_valid():
    if not REGISTRY_PATH.exists():
        pytest.skip("participant_registry.csv is a local research dataset")
    df = pd.read_csv(REGISTRY_PATH)
    assert len(df) == 2960, "Manifest must cover all 2,960 scanned files"
    assert df["participant_id"].isna().sum() == 0, "All rows must have a valid participant_id"
    assert df["diagnostic_group"].isna().sum() == 0, "All rows must have a diagnostic_group"
    assert (df["qc_pass"] == True).sum() == 1961, "Must have exactly 1,961 analysis-ready transcripts"


def test_canonical_features_synchronized_exports():
    if not PARQUET_PATH.exists():
        pytest.skip("canonical_features.parquet is a local research dataset")
    assert CSV_PATH.exists(), "canonical_features.csv must exist"
    assert XLSX_PATH.exists(), "canonical_features.xlsx must exist"

    df_parquet = pd.read_parquet(PARQUET_PATH)
    df_csv = pd.read_csv(CSV_PATH)
    df_xlsx = pd.read_excel(XLSX_PATH, sheet_name="Features")

    assert len(df_parquet) == 1961, "Must contain exactly 1,961 analysis-ready rows"
    assert len(df_csv) == 1961
    assert df_parquet.columns.tolist() == df_csv.columns.tolist()

    assert len(df_xlsx) == 1961
    assert df_parquet.columns.tolist() == df_xlsx.columns.tolist()

    # Numerical consistency check
    feature_cols = [f for f in FEATURES if f != "age_months" and f in df_parquet.columns]
    for col in feature_cols:
        np.testing.assert_allclose(
            df_parquet[col].values,
            df_csv[col].values,
            rtol=1e-5,
            atol=1e-5,
        )


def test_group_kfold_zero_participant_leakage():
    if not PARQUET_PATH.exists():
        pytest.skip("canonical_features.parquet is a local research dataset")
    df = pd.read_parquet(PARQUET_PATH)

    gkf = GroupKFold(n_splits=5)
    groups = df["participant_id"].values
    X = df[[f for f in FEATURES if f != "age_months"]].values
    y = (df["diagnostic_group"] == "ASD").astype(int).values

    for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups)):
        train_participants = set(df.iloc[train_idx]["participant_id"])
        test_participants = set(df.iloc[test_idx]["participant_id"])
        overlap = train_participants.intersection(test_participants)
        assert len(overlap) == 0, f"Fold {fold} has participant leakage! Overlap: {overlap}"


def test_fold_isolated_resampling():
    X_fake = np.array([[1.0, 2.0], [1.1, 2.1], [1.2, 1.9], [10.0, 10.0], [10.1, 10.2], [10.3, 10.1], [10.2, 9.9]])
    y_fake = np.array([1, 1, 1, 0, 0, 0, 0])

    X_none, y_none = apply_resampling(X_fake, y_fake, "none")
    assert len(X_none) == len(X_fake)

    X_sm, y_sm = apply_resampling(X_fake, y_fake, "smote")
    assert len(X_sm) == 8
    assert (y_sm == 1).sum() == 4
    assert (y_sm == 0).sum() == 4

    X_ros, y_ros = apply_resampling(X_fake, y_fake, "random_oversample")
    assert len(X_ros) == 8
    assert (y_ros == 1).sum() == 4


def test_compute_metrics_correctness():
    y_true = np.array([1, 1, 0, 0])
    y_prob = np.array([0.9, 0.8, 0.1, 0.2])
    m = compute_metrics(y_true, y_prob)

    assert m["auroc"] == 1.0
    assert m["sensitivity"] == 1.0
    assert m["specificity"] == 1.0
    assert m["balanced_acc"] == 1.0
    assert m["f1"] == 1.0
    assert m["brier"] < 0.05
