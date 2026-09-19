"""Extract canonical features v2 (features-conversation-v2) across all analysis-ready transcripts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.features.transcript_features import extract_transcript_features
from src.feature_schema import (
    CONVERSATION_V2_FEATURES,
    FEATURE_DOCS,
    FEATURE_SCHEMA_V2_VERSION,
    FEATURES,
    FEATURES_V2,
)


DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_PATH = DATA_DIR / "ml" / "participant_registry.csv"
OUTPUT_PARQUET = DATA_DIR / "ml" / "canonical_features_v2.parquet"
OUTPUT_CSV = DATA_DIR / "ml" / "canonical_features_v2.csv"
OUTPUT_XLSX = DATA_DIR / "ml" / "canonical_features_v2.xlsx"
OUTPUT_MANIFEST = DATA_DIR / "ml" / "canonical_features_v2.manifest.json"


def pseudonymous_research_id(kind: str, *source_parts: object) -> str:
    """Return a stable, non-source-linked identifier for committed exports."""
    if kind not in {"participant", "session"}:
        raise ValueError("kind must be 'participant' or 'session'")
    source = "\x00".join(str(part) for part in source_parts)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"research-{kind}-{digest}"


def extract_all_canonical_features_v2() -> pd.DataFrame:
    """Extract canonical features v2 strictly matching participant_registry."""
    registry_df = pd.read_csv(REGISTRY_PATH)
    ready_df = registry_df[registry_df["qc_pass"] == True].copy()

    extracted_rows: list[dict[str, Any]] = []

    for item in ready_df.to_dict(orient="records"):
        participant_uid = pseudonymous_research_id(
            "participant", item["corpus"], item["participant_uid"]
        )
        session_id = pseudonymous_research_id(
            "session",
            item["corpus"],
            item["participant_uid"],
            item["session_id"],
            item["session_order"],
        )
        source_path = PROJECT_ROOT / item["source_file"]
        curated_path = PROJECT_ROOT / item["curated_path"]

        target_path = curated_path if curated_path.exists() else source_path
        if not target_path.exists():
            raise FileNotFoundError(
                f"missing analysis-ready transcript for {session_id}"
            )

        age_m = item.get("age_months")
        if pd.isna(age_m):
            age_m = None
        else:
            age_m = float(age_m)

        try:
            res = extract_transcript_features(target_path, age_months=age_m)
            canon_v2 = res.get("canonical_features_v2", {})
        except Exception as exc:
            raise RuntimeError(
                f"feature extraction failed for {session_id}"
            ) from exc

        missing_features = [
            feature
            for feature in FEATURES_V2
            if feature != "age_months" and canon_v2.get(feature) is None
        ]
        if missing_features:
            raise RuntimeError(
                "feature extraction produced incomplete schema for analysis-ready row "
                f"{session_id}: {missing_features}"
            )

        row = {
            "participant_uid": participant_uid,
            "participant_id": participant_uid,
            "session_id": session_id,
            "session_order": item["session_order"],
            "corpus": item["corpus"],
            "diagnostic_group": item["diagnostic_group"],
            "age_months": age_m,
            "sex": item["sex"],
            "language": item["language"],
            "task_type": item["task_type"],
            "recording_context": item["recording_context"],
            "feature_extractor_version": "features-conversation-v2",
            "qc_status": "pass",
        }

        # Append all v2 features
        for feat in FEATURES_V2:
            if feat == "age_months":
                continue  # Already captured in metadata
            row[feat] = canon_v2.get(feat)

        extracted_rows.append(row)

    df = pd.DataFrame(extracted_rows)
    if len(df) != len(ready_df):
        raise RuntimeError(
            f"incomplete v2 export: extracted {len(df)} of {len(ready_df)} analysis-ready rows"
        )

    # Reorder columns: metadata first, then features
    meta_cols = [
        "participant_uid",
        "participant_id",
        "session_id",
        "session_order",
        "corpus",
        "diagnostic_group",
        "age_months",
        "sex",
        "language",
        "task_type",
        "recording_context",
        "feature_extractor_version",
        "qc_status",
    ]
    feature_cols = [f for f in FEATURES_V2 if f != "age_months"]
    df = df[meta_cols + feature_cols]

    # Export synchronized Parquet, CSV, XLSX
    OUTPUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PARQUET, index=False)
    df.to_csv(OUTPUT_CSV, index=False)

    # Build multi-tab Excel artifact
    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Features_v2", index=False)

        # Participants sheet
        participants_df = (
            df.groupby("participant_id")
            .agg(
                corpus=("corpus", "first"),
                diagnostic_group=("diagnostic_group", "first"),
                total_sessions=("session_id", "count"),
                min_age=("age_months", "min"),
                max_age=("age_months", "max"),
                sex=("sex", "first"),
                task_type=("task_type", "first"),
            )
            .reset_index()
        )
        participants_df.to_excel(writer, sheet_name="Participants", index=False)

        # Class Distribution sheet
        class_dist = pd.DataFrame({
            "Sessions": df["diagnostic_group"].value_counts(),
            "Unique_Participants": df.groupby("diagnostic_group")["participant_id"].nunique(),
        }).reset_index().rename(columns={"index": "diagnostic_group"})
        class_dist.to_excel(writer, sheet_name="Class_Distribution", index=False)

        # Missing Values sheet
        missing_df = pd.DataFrame({
            "missing_count": df.isna().sum(),
            "missing_pct": (df.isna().mean() * 100).round(2),
        }).reset_index().rename(columns={"index": "column"})
        missing_df.to_excel(writer, sheet_name="Missing_Values", index=False)

        # Corpus Distribution sheet
        corpus_dist = pd.crosstab(df["corpus"], df["diagnostic_group"])
        corpus_dist.to_excel(writer, sheet_name="Corpus_Distribution")

        # Feature Definitions sheet
        feat_defs = []
        for feat in FEATURES_V2:
            doc = FEATURE_DOCS.get(feat)
            feat_defs.append({
                "feature_name": feat,
                "title": doc.title if doc else feat,
                "category": doc.group if doc else "N/A",
                "formula": doc.formula if doc else "N/A",
                "clinical_meaning": doc.clinical_meaning if doc else "N/A",
                "caveat": doc.caveat if doc else "N/A",
            })
        pd.DataFrame(feat_defs).to_excel(writer, sheet_name="Feature_Definitions_v2", index=False)

        # QC Summary sheet
        qc_summary = pd.DataFrame([
            {"metric": "Total Analysis-Ready Transcripts", "value": len(df)},
            {"metric": "Unique Participants", "value": df["participant_id"].nunique()},
            {"metric": "Total Canonical Features (v2)", "value": len(feature_cols) + 1},
            {"metric": "Schema Version", "value": "features-conversation-v2"},
            {"metric": "Parquet Export", "value": str(OUTPUT_PARQUET.name)},
            {"metric": "CSV Export", "value": str(OUTPUT_CSV.name)},
        ])
        qc_summary.to_excel(writer, sheet_name="QC_Summary", index=False)

    artifacts = []
    for artifact_path in (OUTPUT_PARQUET, OUTPUT_CSV, OUTPUT_XLSX):
        artifacts.append({
            "path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": artifact_path.stat().st_size,
            "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        })
    manifest = {
        "schema_version": FEATURE_SCHEMA_V2_VERSION,
        "feature_extractor_version": "features-conversation-v2",
        "row_count": len(df),
        "participant_count": int(df["participant_id"].nunique()),
        "features": FEATURES_V2,
        "artifacts": artifacts,
    }
    OUTPUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Canonical features v2 exported:")
    print(f"  Parquet: {OUTPUT_PARQUET} ({len(df)} rows)")
    print(f"  CSV:     {OUTPUT_CSV}")
    print(f"  Excel:   {OUTPUT_XLSX}")
    print(f"  Manifest:{OUTPUT_MANIFEST}")
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract canonical features v2 across all analysis-ready transcripts.")
    args = parser.parse_args()
    extract_all_canonical_features_v2()
    return 0


if __name__ == "__main__":
    sys.exit(main())
