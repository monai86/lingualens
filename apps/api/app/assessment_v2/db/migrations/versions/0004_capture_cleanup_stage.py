"""Allow durable cleanup processing runs for tombstoned recordings."""

from alembic import op


revision = "0004_capture_cleanup_stage"
down_revision = "0003_capture_protocols_recordings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("processing_runs") as batch:
        batch.drop_constraint("ck_processing_runs_stage", type_="check")
        batch.create_check_constraint(
            "ck_processing_runs_stage",
            "stage IN ('upload_verification', 'quality_analysis', 'cleanup')",
        )


def downgrade() -> None:
    with op.batch_alter_table("processing_runs") as batch:
        batch.drop_constraint("ck_processing_runs_stage", type_="check")
        batch.create_check_constraint(
            "ck_processing_runs_stage",
            "stage IN ('upload_verification', 'quality_analysis')",
        )
