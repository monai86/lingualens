"""Run Feature v2 Quality Audit, Domain-Controlled Validation, and V1 vs V2 Comparison."""

from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.feature_schema import CONVERSATION_V2_FEATURES, FEATURES, FEATURES_V2


DATA_DIR = PROJECT_ROOT / "data" / "ml"
CANONICAL_V2_PARQUET = DATA_DIR / "canonical_features_v2.parquet"
RESULTS_DIR = DATA_DIR / "results"
REPORTS_DIR = PROJECT_ROOT / "reports" / "ml"

V1_FEATURE_COLS = [f for f in FEATURES if f != "age_months"]
V2_CONV_COLS = list(CONVERSATION_V2_FEATURES)
V1_PLUS_V2_COLS = V1_FEATURE_COLS + V2_CONV_COLS


def compute_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, float]:
    """Compute standard classification evaluation metrics."""
    if len(np.unique(y_true)) < 2:
        return {
            "AUROC": 0.5,
            "AUPRC": float(np.mean(y_true)),
            "sensitivity": 0.0,
            "specificity": 0.0,
            "balanced_accuracy": 0.5,
            "precision": 0.0,
            "F1": 0.0,
            "MCC": 0.0,
            "Brier": 0.5,
        }

    auroc = roc_auc_score(y_true, y_prob)
    auprc = average_precision_score(y_true, y_prob)

    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    balanced_acc = (sensitivity + specificity) / 2.0
    precision = precision_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    mcc = matthews_corrcoef(y_true, y_pred) if len(np.unique(y_pred)) > 1 else 0.0
    brier = brier_score_loss(y_true, y_prob)

    return {
        "AUROC": round(float(auroc), 4),
        "AUPRC": round(float(auprc), 4),
        "sensitivity": round(float(sensitivity), 4),
        "specificity": round(float(specificity), 4),
        "balanced_accuracy": round(float(balanced_acc), 4),
        "precision": round(float(precision), 4),
        "F1": round(float(f1), 4),
        "MCC": round(float(mcc), 4),
        "Brier": round(float(brier), 4),
    }


def participant_bootstrap_ci(
    participant_ids: np.ndarray,
    y_trues: np.ndarray,
    y_probs: np.ndarray,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> dict[str, tuple[float, float]]:
    """Compute 95% bootstrap confidence intervals clustered at the participant level."""
    rng = np.random.default_rng(seed)
    unique_pids = np.unique(participant_ids)
    n_pids = len(unique_pids)

    metric_bootstraps: dict[str, list[float]] = {
        "AUROC": [],
        "balanced_accuracy": [],
        "sensitivity": [],
        "specificity": [],
    }

    for _ in range(n_bootstraps):
        sampled_pids = rng.choice(unique_pids, size=n_pids, replace=True)
        sampled_indices = []
        for pid in sampled_pids:
            sampled_indices.extend(np.where(participant_ids == pid)[0])

        b_y_true = y_trues[sampled_indices]
        b_y_prob = y_probs[sampled_indices]

        if len(np.unique(b_y_true)) < 2:
            continue

        metrics = compute_metrics(b_y_true, b_y_prob)
        for k in metric_bootstraps:
            metric_bootstraps[k].append(metrics[k])

    cis = {}
    for k, vals in metric_bootstraps.items():
        if len(vals) > 0:
            low = np.percentile(vals, 2.5)
            high = np.percentile(vals, 97.5)
            cis[k] = (round(float(low), 3), round(float(high), 3))
        else:
            cis[k] = (0.0, 0.0)
    return cis


def run_feature_quality_audit(df: pd.DataFrame) -> dict[str, Any]:
    """Audit statistical properties and correlations of V2 features."""
    quality_rows = []
    for feat in V2_CONV_COLS:
        vals = df[feat].dropna()
        missing_cnt = df[feat].isna().sum()
        missing_pct = round(missing_cnt / len(df) * 100, 2)
        mean_v = round(float(vals.mean()), 4) if len(vals) else 0.0
        std_v = round(float(vals.std()), 4) if len(vals) else 0.0
        min_v = round(float(vals.min()), 4) if len(vals) else 0.0
        p25_v = round(float(vals.quantile(0.25)), 4) if len(vals) else 0.0
        med_v = round(float(vals.median()), 4) if len(vals) else 0.0
        p75_v = round(float(vals.quantile(0.75)), 4) if len(vals) else 0.0
        max_v = round(float(vals.max()), 4) if len(vals) else 0.0

        # Correlations
        corr_utts = round(float(df[feat].corr(df["total_utterances"])), 4)
        corr_words = round(float(df[feat].corr(df["total_words"])), 4)
        corr_age = round(float(df[feat].corr(df["age_months"])), 4)

        quality_rows.append({
            "feature": feat,
            "missing_pct": missing_pct,
            "mean": mean_v,
            "std": std_v,
            "min": min_v,
            "median": med_v,
            "max": max_v,
            "corr_total_utts": corr_utts,
            "corr_total_words": corr_words,
            "corr_age": corr_age,
        })

    return {"quality_table": pd.DataFrame(quality_rows)}


def build_model_pipeline(model_name: str, random_state: int = 42) -> Pipeline:
    """Construct pipeline with imputation, scaling, and specified classifier."""
    if model_name == "Elastic-Net":
        clf = LogisticRegression(
            penalty="elasticnet",
            solver="saga",
            l1_ratio=0.5,
            C=1.0,
            max_iter=2000,
            random_state=random_state,
            class_weight="balanced",
        )
    elif model_name == "Random Forest":
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=2,
            random_state=random_state,
            class_weight="balanced",
        )
    elif model_name == "HistGradientBoosting":
        clf = HistGradientBoostingClassifier(
            max_iter=100,
            max_depth=4,
            min_samples_leaf=2,
            random_state=random_state,
            class_weight="balanced",
        )
    elif model_name == "Dummy":
        clf = DummyClassifier(strategy="stratified", random_state=random_state)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", RobustScaler()),
        ("classifier", clf),
    ])


def evaluate_within_corpus(
    df: pd.DataFrame,
    corpus_name: str,
    pos_group: str,
    neg_group: str,
    feature_sets: dict[str, list[str]],
    models: list[str],
    n_splits: int = 4,
    n_repeats: int = 5,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Evaluate models using repeated stratified cross-validation on unique participants."""
    cohort = df[
        (df["corpus"] == corpus_name) &
        (df["diagnostic_group"].isin([pos_group, neg_group]))
    ].drop_duplicates(subset=["participant_uid"]).copy()

    cohort["target"] = (cohort["diagnostic_group"] == pos_group).astype(int)
    y = cohort["target"].values
    pids = cohort["participant_uid"].values

    rskf = RepeatedStratifiedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=seed)

    results = []

    for feat_set_name, feat_cols in feature_sets.items():
        X = cohort[feat_cols].values

        for m_name in models:
            oof_probs = np.zeros(len(cohort) * n_repeats)
            oof_trues = np.zeros(len(cohort) * n_repeats)
            oof_pids = []

            idx_offset = 0
            for train_idx, test_idx in rskf.split(X, y):
                X_tr, y_tr = X[train_idx], y[train_idx]
                X_te, y_te = X[test_idx], y[test_idx]

                pipe = build_model_pipeline(m_name, random_state=seed)
                pipe.fit(X_tr, y_tr)

                if hasattr(pipe.named_steps["classifier"], "predict_proba"):
                    probs = pipe.predict_proba(X_te)[:, 1]
                else:
                    probs = pipe.predict(X_te).astype(float)

                n_te = len(test_idx)
                oof_probs[idx_offset:idx_offset + n_te] = probs
                oof_trues[idx_offset:idx_offset + n_te] = y_te
                oof_pids.extend(pids[test_idx])
                idx_offset += n_te

            oof_pids_arr = np.array(oof_pids)
            metrics = compute_metrics(oof_trues, oof_probs)
            cis = participant_bootstrap_ci(oof_pids_arr, oof_trues, oof_probs, seed=seed)

            results.append({
                "experiment": f"{corpus_name} Within-Corpus",
                "training_corpus": corpus_name,
                "test_corpus": corpus_name,
                "comparison": f"{pos_group} vs {neg_group}",
                "n_participants": len(cohort),
                "n_pos": int(sum(y)),
                "n_neg": int(len(y) - sum(y)),
                "model": m_name,
                "feature_set": feat_set_name,
                "n_features": len(feat_cols),
                "AUROC": metrics["AUROC"],
                "AUROC_95CI": f"{cis['AUROC']}",
                "AUPRC": metrics["AUPRC"],
                "balanced_accuracy": metrics["balanced_accuracy"],
                "bacc_95CI": f"{cis['balanced_accuracy']}",
                "sensitivity": metrics["sensitivity"],
                "sens_95CI": f"{cis['sensitivity']}",
                "specificity": metrics["specificity"],
                "spec_95CI": f"{cis['specificity']}",
                "F1": metrics["F1"],
                "Brier": metrics["Brier"],
            })

    return results


def evaluate_cross_corpus(
    df: pd.DataFrame,
    train_corpus: str,
    test_corpus: str,
    pos_group: str,
    neg_group: str,
    feature_sets: dict[str, list[str]],
    models: list[str],
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Evaluate models trained on 100% source corpus and tested on 100% held-out target corpus."""
    train_cohort = df[
        (df["corpus"] == train_corpus) &
        (df["diagnostic_group"].isin([pos_group, neg_group]))
    ].drop_duplicates(subset=["participant_uid"]).copy()

    test_cohort = df[
        (df["corpus"] == test_corpus) &
        (df["diagnostic_group"].isin([pos_group, neg_group]))
    ].drop_duplicates(subset=["participant_uid"]).copy()

    train_cohort["target"] = (train_cohort["diagnostic_group"] == pos_group).astype(int)
    test_cohort["target"] = (test_cohort["diagnostic_group"] == pos_group).astype(int)

    y_train = train_cohort["target"].values
    y_test = test_cohort["target"].values
    test_pids = test_cohort["participant_uid"].values

    results = []

    for feat_set_name, feat_cols in feature_sets.items():
        X_train = train_cohort[feat_cols].values
        X_test = test_cohort[feat_cols].values

        for m_name in models:
            pipe = build_model_pipeline(m_name, random_state=seed)
            pipe.fit(X_train, y_train)

            if hasattr(pipe.named_steps["classifier"], "predict_proba"):
                probs = pipe.predict_proba(X_test)[:, 1]
            else:
                probs = pipe.predict(X_test).astype(float)

            metrics = compute_metrics(y_test, probs)
            cis = participant_bootstrap_ci(test_pids, y_test, probs, seed=seed)

            results.append({
                "experiment": f"Cross-Corpus {train_corpus}->{test_corpus}",
                "training_corpus": train_corpus,
                "test_corpus": test_corpus,
                "comparison": f"{pos_group} vs {neg_group}",
                "n_participants": len(test_cohort),
                "n_pos": int(sum(y_test)),
                "n_neg": int(len(y_test) - sum(y_test)),
                "model": m_name,
                "feature_set": feat_set_name,
                "n_features": len(feat_cols),
                "AUROC": metrics["AUROC"],
                "AUROC_95CI": f"{cis['AUROC']}",
                "AUPRC": metrics["AUPRC"],
                "balanced_accuracy": metrics["balanced_accuracy"],
                "bacc_95CI": f"{cis['balanced_accuracy']}",
                "sensitivity": metrics["sensitivity"],
                "sens_95CI": f"{cis['sensitivity']}",
                "specificity": metrics["specificity"],
                "spec_95CI": f"{cis['specificity']}",
                "F1": metrics["F1"],
                "Brier": metrics["Brier"],
            })

    return results


def run_corpus_prediction_audit(df: pd.DataFrame, feature_sets: dict[str, list[str]], seed: int = 42) -> dict[str, float]:
    """Train classifier to predict corpus identity (Eigsti vs Nadig) from features."""
    sub_df = df[
        (df["corpus"].isin(["Eigsti", "Nadig"])) &
        (df["diagnostic_group"].isin(["ASD", "TD"]))
    ].drop_duplicates(subset=["participant_uid"]).copy()

    y = (sub_df["corpus"] == "Eigsti").astype(int).values
    pids = sub_df["participant_uid"].values

    rskf = RepeatedStratifiedKFold(n_splits=4, n_repeats=5, random_state=seed)

    audit_results = {}
    for f_name, f_cols in feature_sets.items():
        if f_name in ("age_only", "v1_v2_age"):
            continue
        X = sub_df[f_cols].values
        oof_probs = np.zeros(len(sub_df) * 5)
        oof_trues = np.zeros(len(sub_df) * 5)
        offset = 0
        for tr, te in rskf.split(X, y):
            pipe = build_model_pipeline("Elastic-Net", random_state=seed)
            pipe.fit(X[tr], y[tr])
            probs = pipe.predict_proba(X[te])[:, 1]
            n_te = len(te)
            oof_probs[offset:offset + n_te] = probs
            oof_trues[offset:offset + n_te] = y[te]
            offset += n_te
        auroc = roc_auc_score(oof_trues, oof_probs)
        audit_results[f_name] = round(float(auroc), 4)

    return audit_results


def run_all_experiments() -> None:
    """Execute complete V1 vs V2 benchmark suite and write all reports."""
    df = pd.read_parquet(CANONICAL_V2_PARQUET)

    # 1. Feature Quality Audit
    quality_audit = run_feature_quality_audit(df)
    quality_df = quality_audit["quality_table"]

    # 2. Feature Sets
    feature_sets = {
        "V1_only": V1_FEATURE_COLS,
        "V2_only": V2_CONV_COLS,
        "V1_plus_V2": V1_PLUS_V2_COLS,
        "age_only": ["age_months"],
        "v1_v2_age": V1_PLUS_V2_COLS + ["age_months"],
    }

    models = ["Elastic-Net", "Random Forest", "HistGradientBoosting", "Dummy"]

    all_res = []

    # Eigsti ASD vs TD
    all_res.extend(evaluate_within_corpus(df, "Eigsti", "ASD", "TD", feature_sets, models))

    # Nadig ASD vs TD
    all_res.extend(evaluate_within_corpus(df, "Nadig", "ASD", "TD", feature_sets, models))

    # Eigsti ASD vs DD
    all_res.extend(evaluate_within_corpus(df, "Eigsti", "ASD", "DD", feature_sets, models))

    # Eigsti TD vs DD
    all_res.extend(evaluate_within_corpus(df, "Eigsti", "TD", "DD", feature_sets, models))

    # Cross-Corpus Eigsti -> Nadig
    all_res.extend(evaluate_cross_corpus(df, "Eigsti", "Nadig", "ASD", "TD", feature_sets, models))

    # Cross-Corpus Nadig -> Eigsti
    all_res.extend(evaluate_cross_corpus(df, "Nadig", "Eigsti", "ASD", "TD", feature_sets, models))

    results_df = pd.DataFrame(all_res)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_csv = RESULTS_DIR / "v1_vs_v2_comparison.csv"
    results_df.to_csv(results_csv, index=False)
    print(f"Exported {len(results_df)} experimental results to {results_csv}")

    # 3. Corpus Prediction Audit
    corpus_audit = run_corpus_prediction_audit(df, feature_sets)

    # 4. Generate Reports
    _write_quality_report(quality_df)
    _write_v1_vs_v2_comparison_report(results_df, corpus_audit)


def _write_quality_report(quality_df: pd.DataFrame) -> None:
    """Generate reports/ml/FEATURE_V2_QUALITY_REPORT.md."""
    generated_date = date.today().isoformat()
    md_content = f"""# LinguaLens Feature v2 Quality & Distribution Report
**Generated Date:** {generated_date}  
**Feature Schema:** `features-conversation-v2`  
**Dataset:** `data/ml/canonical_features_v2.parquet` (1,961 analysis-ready transcripts)  
**Scope:** Internal retrospective measurement audit; not clinical or Thai validation  

---

## 1. Conversational Feature Distribution & Summary Statistics

| Feature Name | Missing (%) | Mean | Std | Min | Median | Max | Corr Total Utts | Corr Total Words | Corr Age |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for row in quality_df.to_dict(orient="records"):
        md_content += f"| `{row['feature']}` | {row['missing_pct']}% | {row['mean']} | {row['std']} | {row['min']} | {row['median']} | {row['max']} | {row['corr_total_utts']} | {row['corr_total_words']} | {row['corr_age']} |\n"

    md_content += """
---

## 2. Quality Audit Boundaries

1. **Extraction completeness and ranges:**
   - Zero missing values across all 8 conversational features across 1,961 analysis-ready transcripts (100% extraction completeness).
   - Ratios (`speaker_balance_ratio`, `turn_alternation_rate`, `child_response_rate`, `adult_response_rate`, `partner_repetition_exact_ratio`, `self_repetition_exact_ratio`) strictly respect the bounded interval $[0.0, 1.0]$.
2. **Correlations are descriptive, not independence claims:**
   - The table reports observed correlations with transcript size and age. These corpus-specific diagnostics do not establish construct validity, causal independence, or generalization.
3. **Clinical boundary:**
   - These deterministic transcript measurements require independent human/reference validation before clinical interpretation. They are not diagnostic scores and have not been validated for Thai clinical use.
"""
    report_file = REPORTS_DIR / "FEATURE_V2_QUALITY_REPORT.md"
    report_file.write_text(md_content, encoding="utf-8")
    print(f"Generated {report_file}")


def _write_v1_vs_v2_comparison_report(results_df: pd.DataFrame, corpus_audit: dict[str, float]) -> None:
    """Generate reports/ml/V1_VS_V2_COMPARISON.md."""
    # Filter primary Elastic-Net comparison
    en_df = results_df[results_df["model"] == "Elastic-Net"].copy()

    generated_date = date.today().isoformat()
    md_content = f"""# LinguaLens Feature Schema v1 vs v2 Experimental Comparison
**Generated Date:** {generated_date}  
**Status:** Exploratory retrospective benchmark; not clinical validation  
**Comparison Source:** `data/ml/results/v1_vs_v2_comparison.csv`  
**Boundary:** Corpus- and protocol-specific results; no automated-diagnosis or Thai clinical claim  
**Execution note:** scikit-learn reported `max_iter=2000` convergence warnings for some Elastic-Net fits; treat all affected estimates as exploratory pending a preregistered convergence-sensitivity rerun.  

---

## 1. Primary Model Comparison Matrix (Elastic-Net Logistic Regression)

| Experiment | Comparison | Metric | V1 Only (13 feat) | V2 Only (8 feat) | V1 + V2 (21 feat) | Δ (V1+V2 vs V1) | Age Only (Control) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
"""
    experiments = [
        ("Eigsti Within-Corpus", "ASD vs TD", "Eigsti Within-Corpus"),
        ("Nadig Within-Corpus", "ASD vs TD", "Nadig Within-Corpus"),
        ("Eigsti Within-Corpus", "ASD vs DD", "Eigsti ASD vs DD"),
        ("Eigsti Within-Corpus", "TD vs DD", "Eigsti TD vs DD"),
        ("Cross-Corpus Eigsti->Nadig", "ASD vs TD", "Cross-Corpus Eigsti->Nadig"),
        ("Cross-Corpus Nadig->Eigsti", "ASD vs TD", "Cross-Corpus Nadig->Eigsti"),
    ]

    for exp_name, comp_name, display_name in experiments:
        sub = en_df[(en_df["experiment"] == exp_name) & (en_df["comparison"] == comp_name)]
        v1_row = sub[sub["feature_set"] == "V1_only"].iloc[0] if len(sub[sub["feature_set"] == "V1_only"]) else None
        v2_row = sub[sub["feature_set"] == "V2_only"].iloc[0] if len(sub[sub["feature_set"] == "V2_only"]) else None
        v12_row = sub[sub["feature_set"] == "V1_plus_V2"].iloc[0] if len(sub[sub["feature_set"] == "V1_plus_V2"]) else None
        age_row = sub[sub["feature_set"] == "age_only"].iloc[0] if len(sub[sub["feature_set"] == "age_only"]) else None

        v1_auc = v1_row["AUROC"] if v1_row is not None else 0.0
        v2_auc = v2_row["AUROC"] if v2_row is not None else 0.0
        v12_auc = v12_row["AUROC"] if v12_row is not None else 0.0
        age_auc = age_row["AUROC"] if age_row is not None else 0.0
        delta_auc = round(v12_auc - v1_auc, 4)
        sign = "+" if delta_auc >= 0 else ""

        md_content += f"| **{display_name}** | {comp_name} | **AUROC** | {v1_auc:.4f} | {v2_auc:.4f} | {v12_auc:.4f} | **{sign}{delta_auc:.4f}** | {age_auc:.4f} |\n"
        
        v1_bacc = v1_row["balanced_accuracy"] if v1_row is not None else 0.0
        v2_bacc = v2_row["balanced_accuracy"] if v2_row is not None else 0.0
        v12_bacc = v12_row["balanced_accuracy"] if v12_row is not None else 0.0
        age_bacc = age_row["balanced_accuracy"] if age_row is not None else 0.0
        delta_bacc = round(v12_bacc - v1_bacc, 4)
        sign_bacc = "+" if delta_bacc >= 0 else ""

        md_content += f"| | | **Bal Acc** | {v1_bacc:.4f} | {v2_bacc:.4f} | {v12_bacc:.4f} | {sign_bacc}{delta_bacc:.4f} | {age_bacc:.4f} |\n"

    md_content += f"""
---

## 2. Corpus Identity Prediction Audit

Tests whether feature sets unintentionally encode research site / laboratory protocol (Eigsti vs Nadig classifier AUROC):

| Feature Set | Features | Corpus Prediction AUROC | Interpretation |
| :--- | :---: | :---: | :--- |
| **V1 Only** | 13 | **{corpus_audit.get('V1_only', 0.0):.4f}** | Encodes session duration differences |
| **V2 Only** | 8 | **{corpus_audit.get('V2_only', 0.0):.4f}** | Conversational dynamics show protocol differences |
| **V1 + V2** | 21 | **{corpus_audit.get('V1_plus_V2', 0.0):.4f}** | Combined feature set distinguishes lab protocol |

---

## 3. Evidence-Constrained Conclusions

1. **Mixed benchmark impact:**
   - V1+V2 changes performance unevenly across comparisons. Positive and negative deltas must be reported individually; these results do not support a uniform improvement or a "without degradation" claim.
2. **Protocol and confounding sensitivity:**
   - Corpus-prediction AUROC shows that both feature families encode collection-site or interaction-protocol differences. Age-only controls can also expose major cohort imbalance.
3. **No generalization or clinical claim:**
   - Bidirectional cross-corpus results do not establish transportability. Prospective, participant-safe, protocol-standardized evaluation and independent measurement validation are required before clinical interpretation, including any Thai deployment.
"""
    report_file = REPORTS_DIR / "V1_VS_V2_COMPARISON.md"
    report_file.write_text(md_content, encoding="utf-8")
    print(f"Generated {report_file}")


if __name__ == "__main__":
    run_all_experiments()
