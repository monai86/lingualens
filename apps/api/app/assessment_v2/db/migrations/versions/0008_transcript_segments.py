"""Add immutable transcript segment snapshots and tenant RLS."""

from alembic import op
import sqlalchemy as sa


revision = "0008_transcript_segments"
down_revision = "0007_durable_evidence_jobs"
branch_labels = None
depends_on = None


def _enable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table_name, policy_name in (
        ("transcript_segment_sets", "transcript_segment_sets_organization_isolation"),
        ("transcript_segments", "transcript_segments_organization_isolation"),
    ):
        op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY {policy_name} ON {table_name} "
                "USING (organization_id = current_setting('app.current_organization_id', true)) "
                "WITH CHECK (organization_id = current_setting('app.current_organization_id', true))"
            )
        )


def _disable_tenant_rls() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    # A downgrade guard must see every tenant before the tables are removed.
    # Forced RLS otherwise makes an empty result tenant-local and could allow
    # populated segment data to be dropped silently.
    op.execute("ALTER TABLE transcript_segments NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE transcript_segments DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE transcript_segment_sets NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE transcript_segment_sets DISABLE ROW LEVEL SECURITY")
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS transcript_segments_organization_isolation "
            "ON transcript_segments"
        )
    )
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS transcript_segment_sets_organization_isolation "
            "ON transcript_segment_sets"
        )
    )


def upgrade() -> None:
    op.create_table(
        "transcript_segment_sets",
        sa.Column("transcript_segment_set_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("assessment_id", sa.String(length=64), nullable=False),
        sa.Column("transcript_revision_id", sa.String(length=64), nullable=False),
        sa.Column("transcript_content_sha256", sa.String(length=64), nullable=False),
        sa.Column("recording_id", sa.String(length=64), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("review_state", sa.String(length=32), nullable=False),
        sa.Column("segments_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=128), nullable=False),
        sa.Column("attested_by_user_id", sa.String(length=128), nullable=True),
        sa.Column("attested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_segment_sets_organization",
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessments.assessment_id"],
            name="fk_segment_sets_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["transcript_revision_id"],
            ["transcript_revisions.transcript_revision_id"],
            name="fk_segment_sets_transcript",
        ),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recordings.recording_id"],
            name="fk_segment_sets_recording",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "assessment_id"],
            ["assessments.organization_id", "assessments.assessment_id"],
            name="fk_segment_sets_assessment_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "transcript_revision_id"],
            [
                "transcript_revisions.organization_id",
                "transcript_revisions.transcript_revision_id",
            ],
            name="fk_segment_sets_transcript_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "recording_id"],
            ["recordings.organization_id", "recordings.recording_id"],
            name="fk_segment_sets_recording_tenant",
        ),
        sa.PrimaryKeyConstraint(
            "transcript_segment_set_id",
            name="pk_transcript_segment_sets",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "transcript_segment_set_id",
            name="uq_segment_sets_organization_set_id",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "assessment_id",
            "revision",
            name="uq_segment_sets_organization_assessment_revision",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'asr_draft', 'imported')",
            name="ck_segment_sets_source",
        ),
        sa.CheckConstraint(
            "review_state IN ('draft', 'attested', 'superseded')",
            name="ck_segment_sets_review_state",
        ),
        sa.CheckConstraint(
            "length(segments_sha256) = 64",
            name="ck_segment_sets_sha256",
        ),
        sa.CheckConstraint(
            "length(transcript_content_sha256) = 64",
            name="ck_segment_sets_transcript_sha256",
        ),
        sa.CheckConstraint(
            "(attested_by_user_id IS NULL AND attested_at IS NULL) OR "
            "(attested_by_user_id IS NOT NULL AND attested_at IS NOT NULL)",
            name="ck_segment_sets_attestation_metadata",
        ),
        sa.CheckConstraint("revision >= 1", name="ck_segment_sets_revision"),
        sa.CheckConstraint("version >= 1", name="ck_segment_sets_version"),
    )
    op.create_index(
        "ix_segment_sets_organization_id",
        "transcript_segment_sets",
        ["organization_id"],
    )
    op.create_index(
        "ix_segment_sets_assessment_id",
        "transcript_segment_sets",
        ["assessment_id"],
    )
    op.create_index(
        "ix_segment_sets_transcript_revision_id",
        "transcript_segment_sets",
        ["transcript_revision_id"],
    )
    op.create_index(
        "ix_segment_sets_recording_id",
        "transcript_segment_sets",
        ["recording_id"],
    )
    op.create_index(
        "ix_segment_sets_organization_assessment_revision",
        "transcript_segment_sets",
        ["organization_id", "assessment_id", "revision"],
    )

    op.create_table(
        "transcript_segments",
        sa.Column("transcript_segment_id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("transcript_segment_set_id", sa.String(length=64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.BigInteger(), nullable=False),
        sa.Column("end_ms", sa.BigInteger(), nullable=False),
        sa.Column("speaker_role", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("uncertainty_reason", sa.String(length=64), server_default=sa.text("'none'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            name="fk_segments_organization",
        ),
        sa.ForeignKeyConstraint(
            ["transcript_segment_set_id"],
            ["transcript_segment_sets.transcript_segment_set_id"],
            name="fk_segments_segment_set",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "transcript_segment_set_id"],
            [
                "transcript_segment_sets.organization_id",
                "transcript_segment_sets.transcript_segment_set_id",
            ],
            name="fk_segments_segment_set_tenant",
        ),
        sa.PrimaryKeyConstraint("transcript_segment_id", name="pk_transcript_segments"),
        sa.UniqueConstraint(
            "organization_id",
            "transcript_segment_id",
            name="uq_segments_organization_segment_id",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "transcript_segment_set_id",
            "ordinal",
            name="uq_segments_organization_set_ordinal",
        ),
        sa.CheckConstraint("ordinal >= 1", name="ck_segments_ordinal"),
        sa.CheckConstraint("start_ms >= 0", name="ck_segments_start_ms"),
        sa.CheckConstraint("end_ms > start_ms", name="ck_segments_end_ms"),
        sa.CheckConstraint(
            "speaker_role IN ('child', 'therapist', 'caregiver', 'unknown')",
            name="ck_segments_speaker_role",
        ),
        sa.CheckConstraint("length(text) > 0", name="ck_segments_text"),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="ck_segments_confidence",
        ),
        sa.CheckConstraint(
            "uncertainty_reason IN ('none', 'low_asr_confidence', 'unintelligible_audio', "
            "'speaker_uncertain', 'timestamp_uncertain', 'manual_review')",
            name="ck_segments_uncertainty_reason",
        ),
    )
    op.create_index(
        "ix_segments_organization_id",
        "transcript_segments",
        ["organization_id"],
    )
    op.create_index(
        "ix_segments_transcript_segment_set_id",
        "transcript_segments",
        ["transcript_segment_set_id"],
    )
    op.create_index(
        "ix_segments_organization_set_ordinal",
        "transcript_segments",
        ["organization_id", "transcript_segment_set_id", "ordinal"],
    )
    _enable_tenant_rls()


def _assert_no_segment_rows(bind) -> None:
    for table_name in ("transcript_segment_sets", "transcript_segments"):
        has_rows = bind.execute(
            sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name})")
        ).scalar()
        if has_rows:
            raise RuntimeError(
                "segment_downgrade_blocked: populated transcript segment tables "
                "must not be silently deleted."
            )


def downgrade() -> None:
    _disable_tenant_rls()
    _assert_no_segment_rows(op.get_bind())
    op.drop_index(
        "ix_segments_organization_set_ordinal",
        table_name="transcript_segments",
    )
    op.drop_index(
        "ix_segments_transcript_segment_set_id",
        table_name="transcript_segments",
    )
    op.drop_index("ix_segments_organization_id", table_name="transcript_segments")
    op.drop_table("transcript_segments")
    op.drop_index(
        "ix_segment_sets_organization_assessment_revision",
        table_name="transcript_segment_sets",
    )
    op.drop_index("ix_segment_sets_recording_id", table_name="transcript_segment_sets")
    op.drop_index(
        "ix_segment_sets_transcript_revision_id",
        table_name="transcript_segment_sets",
    )
    op.drop_index("ix_segment_sets_assessment_id", table_name="transcript_segment_sets")
    op.drop_index("ix_segment_sets_organization_id", table_name="transcript_segment_sets")
    op.drop_table("transcript_segment_sets")
