"""Bind evidence processing and results to immutable transcript segment sets."""

from alembic import op
import sqlalchemy as sa


revision = "0009_segment_evidence_provenance"
down_revision = "0008_transcript_segments"
branch_labels = None
depends_on = None


_SEGMENT_PROVENANCE_CHECK = (
    "(segment_set_id IS NULL AND segment_set_sha256 IS NULL) OR "
    "(segment_set_id IS NOT NULL AND length(segment_set_sha256) = 64)"
)


def _add_columns() -> None:
    op.add_column(
        "processing_runs",
        sa.Column("segment_set_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "processing_runs",
        sa.Column("segment_set_sha256", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "evidence_runs",
        sa.Column("segment_set_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "evidence_runs",
        sa.Column("segment_set_sha256", sa.String(length=64), nullable=True),
    )


def _upgrade_postgresql() -> None:
    op.create_foreign_key(
        "fk_processing_runs_segment_set_tenant",
        "processing_runs",
        "transcript_segment_sets",
        ["organization_id", "segment_set_id"],
        ["organization_id", "transcript_segment_set_id"],
    )
    op.create_foreign_key(
        "fk_evidence_runs_segment_set_tenant",
        "evidence_runs",
        "transcript_segment_sets",
        ["organization_id", "segment_set_id"],
        ["organization_id", "transcript_segment_set_id"],
    )
    op.create_check_constraint(
        "ck_processing_runs_segment_provenance",
        "processing_runs",
        _SEGMENT_PROVENANCE_CHECK,
    )
    op.create_check_constraint(
        "ck_evidence_runs_segment_provenance",
        "evidence_runs",
        _SEGMENT_PROVENANCE_CHECK,
    )
    op.drop_constraint("uq_evidence_runs_identity", table_name="evidence_runs", type_="unique")
    op.create_unique_constraint(
        "uq_evidence_runs_segment_identity",
        "evidence_runs",
        [
            "organization_id",
            "assessment_id",
            "transcript_revision_id",
            "segment_set_id",
            "segment_set_sha256",
            "pipeline_version",
            "feature_schema_version",
        ],
    )


def _upgrade_sqlite() -> None:
    with op.batch_alter_table("processing_runs", recreate="always") as batch:
        batch.create_foreign_key(
            "fk_processing_runs_segment_set_tenant",
            "transcript_segment_sets",
            ["organization_id", "segment_set_id"],
            ["organization_id", "transcript_segment_set_id"],
        )
        batch.create_check_constraint(
            "ck_processing_runs_segment_provenance",
            _SEGMENT_PROVENANCE_CHECK,
        )
    with op.batch_alter_table("evidence_runs", recreate="always") as batch:
        batch.drop_constraint("uq_evidence_runs_identity", type_="unique")
        batch.create_foreign_key(
            "fk_evidence_runs_segment_set_tenant",
            "transcript_segment_sets",
            ["organization_id", "segment_set_id"],
            ["organization_id", "transcript_segment_set_id"],
        )
        batch.create_check_constraint(
            "ck_evidence_runs_segment_provenance",
            _SEGMENT_PROVENANCE_CHECK,
        )
        batch.create_unique_constraint(
            "uq_evidence_runs_segment_identity",
            [
                "organization_id",
                "assessment_id",
                "transcript_revision_id",
                "segment_set_id",
                "segment_set_sha256",
                "pipeline_version",
                "feature_schema_version",
            ],
        )


def _create_indexes() -> None:
    op.create_index(
        "ix_processing_runs_organization_segment_set",
        "processing_runs",
        ["organization_id", "segment_set_id"],
    )
    op.create_index(
        "ix_evidence_runs_organization_segment_set",
        "evidence_runs",
        ["organization_id", "segment_set_id"],
    )


def _disable_evidence_rls_for_downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name in ("processing_runs", "evidence_runs"):
        op.execute(sa.text(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))


def _restore_evidence_rls_after_downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name in ("processing_runs", "evidence_runs"):
        op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))


def upgrade() -> None:
    _add_columns()
    if op.get_bind().dialect.name == "postgresql":
        _upgrade_postgresql()
    else:
        _upgrade_sqlite()
    _create_indexes()


def _assert_no_segment_bound_rows(bind) -> None:
    has_bound_rows = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM processing_runs WHERE segment_set_id IS NOT NULL "
            "UNION ALL "
            "SELECT 1 FROM evidence_runs WHERE segment_set_id IS NOT NULL"
            ")"
        )
    ).scalar()
    if has_bound_rows:
        raise RuntimeError(
            "segment_evidence_provenance_downgrade_blocked: segment-bound rows exist "
            "and must not be deleted."
        )


def _downgrade_postgresql() -> None:
    op.drop_constraint(
        "uq_evidence_runs_segment_identity",
        table_name="evidence_runs",
        type_="unique",
    )
    op.drop_constraint(
        "ck_evidence_runs_segment_provenance",
        table_name="evidence_runs",
        type_="check",
    )
    op.drop_constraint(
        "ck_processing_runs_segment_provenance",
        table_name="processing_runs",
        type_="check",
    )
    op.drop_constraint(
        "fk_evidence_runs_segment_set_tenant",
        table_name="evidence_runs",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_processing_runs_segment_set_tenant",
        table_name="processing_runs",
        type_="foreignkey",
    )
    op.drop_column("evidence_runs", "segment_set_sha256")
    op.drop_column("evidence_runs", "segment_set_id")
    op.drop_column("processing_runs", "segment_set_sha256")
    op.drop_column("processing_runs", "segment_set_id")
    op.create_unique_constraint(
        "uq_evidence_runs_identity",
        "evidence_runs",
        [
            "organization_id",
            "assessment_id",
            "transcript_revision_id",
            "pipeline_version",
            "feature_schema_version",
        ],
    )


def _downgrade_sqlite() -> None:
    with op.batch_alter_table("evidence_runs", recreate="always") as batch:
        batch.drop_constraint("uq_evidence_runs_segment_identity", type_="unique")
        batch.drop_constraint("ck_evidence_runs_segment_provenance", type_="check")
        batch.drop_constraint("fk_evidence_runs_segment_set_tenant", type_="foreignkey")
        batch.drop_column("segment_set_sha256")
        batch.drop_column("segment_set_id")
        batch.create_unique_constraint(
            "uq_evidence_runs_identity",
            [
                "organization_id",
                "assessment_id",
                "transcript_revision_id",
                "pipeline_version",
                "feature_schema_version",
            ],
        )
    with op.batch_alter_table("processing_runs", recreate="always") as batch:
        batch.drop_constraint("ck_processing_runs_segment_provenance", type_="check")
        batch.drop_constraint("fk_processing_runs_segment_set_tenant", type_="foreignkey")
        batch.drop_column("segment_set_sha256")
        batch.drop_column("segment_set_id")


def downgrade() -> None:
    bind = op.get_bind()
    _disable_evidence_rls_for_downgrade()
    try:
        _assert_no_segment_bound_rows(bind)
        op.drop_index(
            "ix_evidence_runs_organization_segment_set",
            table_name="evidence_runs",
        )
        op.drop_index(
            "ix_processing_runs_organization_segment_set",
            table_name="processing_runs",
        )
        if bind.dialect.name == "postgresql":
            _downgrade_postgresql()
        else:
            _downgrade_sqlite()
    finally:
        _restore_evidence_rls_after_downgrade()
