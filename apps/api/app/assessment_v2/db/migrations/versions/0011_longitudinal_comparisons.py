"""Add longitudinal assessment comparisons with tenant RLS.

Revision ID: 0011_longitudinal_comparisons
Revises: 0010_observations_instruments
Create Date: 2026-09-12 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_longitudinal_comparisons"
down_revision = "0010_observations_instruments"
branch_labels = None
depends_on = None


def _enable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name in (
        "assessment_comparisons",
        "assessment_comparison_features",
    ):
        op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
        op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {table_name}_organization_isolation
                ON {table_name}
                FOR ALL
                USING (
                    organization_id = current_setting('app.current_organization_id', true)
                )
                WITH CHECK (
                    organization_id = current_setting('app.current_organization_id', true)
                );
                """
            )
        )


def _disable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name in (
        "assessment_comparison_features",
        "assessment_comparisons",
    ):
        op.execute(sa.text(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY;"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;"))
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS assessment_comparison_features_organization_isolation "
            "ON assessment_comparison_features;"
        )
    )
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS assessment_comparisons_organization_isolation "
            "ON assessment_comparisons;"
        )
    )


def upgrade() -> None:
    op.create_table(
        "assessment_comparisons",
        sa.Column("comparison_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("child_id", sa.String(length=64), nullable=False),
        sa.Column("baseline_assessment_id", sa.String(length=64), nullable=False),
        sa.Column("current_assessment_id", sa.String(length=64), nullable=False),
        sa.Column("baseline_evidence_run_id", sa.String(length=64), nullable=False),
        sa.Column("current_evidence_run_id", sa.String(length=64), nullable=False),
        sa.Column("baseline_evidence_sha256", sa.String(length=64), nullable=False),
        sa.Column("current_evidence_sha256", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=64), server_default="longitudinal_v1", nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("compatible_feature_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("incompatible_feature_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("compared_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_comparisons_organization",
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.child_id"],
            name="fk_comparisons_child",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_assessment_id"],
            ["assessments.assessment_id"],
            name="fk_comparisons_baseline_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["current_assessment_id"],
            ["assessments.assessment_id"],
            name="fk_comparisons_current_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_evidence_run_id"],
            ["evidence_runs.evidence_run_id"],
            name="fk_comparisons_baseline_evidence_run",
        ),
        sa.ForeignKeyConstraint(
            ["current_evidence_run_id"],
            ["evidence_runs.evidence_run_id"],
            name="fk_comparisons_current_evidence_run",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "child_id"],
            ["children.organization_id", "children.child_id"],
            name="fk_comparisons_child_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "baseline_assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_comparisons_baseline_assessment_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "current_assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_comparisons_current_assessment_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "baseline_evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_comparisons_baseline_evidence_run_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "current_evidence_run_id"],
            ["evidence_runs.organization_id", "evidence_runs.evidence_run_id"],
            name="fk_comparisons_current_evidence_run_tenant",
        ),
        sa.PrimaryKeyConstraint("comparison_id"),
        sa.UniqueConstraint("organization_id", "comparison_id", name="uq_comparisons_organization_comparison"),
        sa.UniqueConstraint(
            "organization_id",
            "baseline_evidence_run_id",
            "current_evidence_run_id",
            "policy_version",
            name="uq_comparisons_org_baseline_current_policy",
        ),
    )
    op.create_index("ix_comparisons_organization_child", "assessment_comparisons", ["organization_id", "child_id"])
    op.create_index("ix_comparisons_organization_current", "assessment_comparisons", ["organization_id", "current_assessment_id"])

    op.create_table(
        "assessment_comparison_features",
        sa.Column("comparison_feature_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("comparison_id", sa.String(length=64), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("incompatibility_reasons_json", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("absolute_delta", sa.Float(), nullable=True),
        sa.Column("percent_change", sa.Float(), nullable=True),
        sa.Column("percent_change_limitation", sa.String(length=64), nullable=True),
        sa.Column("numerical_trend", sa.String(length=32), nullable=False),
        sa.Column("clinical_interpretation", sa.String(length=64), server_default="indeterminate", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_comparison_features_organization",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_id"],
            ["assessment_comparisons.comparison_id"],
            name="fk_comparison_features_comparison",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "comparison_id"],
            ["assessment_comparisons.organization_id", "assessment_comparisons.comparison_id"],
            name="fk_comparison_features_comparison_tenant",
        ),
        sa.PrimaryKeyConstraint("comparison_feature_id"),
        sa.UniqueConstraint("organization_id", "comparison_feature_id", name="uq_comparison_features_org_id"),
        sa.UniqueConstraint("organization_id", "comparison_id", "feature_key", name="uq_comparison_features_org_comp_feature"),
    )
    op.create_index("ix_comparison_features_org_comp", "assessment_comparison_features", ["organization_id", "comparison_id"])

    _enable_tenant_rls()


def downgrade() -> None:
    _disable_tenant_rls()
    op.drop_index("ix_comparison_features_org_comp", table_name="assessment_comparison_features")
    op.drop_table("assessment_comparison_features")
    op.drop_index("ix_comparisons_organization_current", table_name="assessment_comparisons")
    op.drop_index("ix_comparisons_organization_child", table_name="assessment_comparisons")
    op.drop_table("assessment_comparisons")
