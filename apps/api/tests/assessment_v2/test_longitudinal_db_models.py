"""Unit tests for Longitudinal Assessment Comparison ORM models and constraints."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.assessment_v2.db.base import AssessmentBase
from app.assessment_v2.db.models import (
    AssessmentComparisonRecord,
    AssessmentComparisonFeatureRecord,
)


def test_longitudinal_comparison_models_exist_and_map_columns() -> None:
    tables = AssessmentBase.metadata.tables
    assert "assessment_comparisons" in tables
    assert "assessment_comparison_features" in tables

    comp_table = tables["assessment_comparisons"]
    assert "comparison_id" in comp_table.columns
    assert "organization_id" in comp_table.columns
    assert "child_id" in comp_table.columns
    assert "baseline_assessment_id" in comp_table.columns
    assert "current_assessment_id" in comp_table.columns
    assert "baseline_evidence_run_id" in comp_table.columns
    assert "current_evidence_run_id" in comp_table.columns
    assert "baseline_evidence_sha256" in comp_table.columns
    assert "current_evidence_sha256" in comp_table.columns
    assert "policy_version" in comp_table.columns
    assert "status" in comp_table.columns
    assert "is_stale" in comp_table.columns

    feat_table = tables["assessment_comparison_features"]
    assert "comparison_feature_id" in feat_table.columns
    assert "comparison_id" in feat_table.columns
    assert "feature_key" in feat_table.columns
    assert "absolute_delta" in feat_table.columns
    assert "percent_change" in feat_table.columns
    assert "percent_change_limitation" in feat_table.columns
    assert "numerical_trend" in feat_table.columns
    assert "clinical_interpretation" in feat_table.columns
