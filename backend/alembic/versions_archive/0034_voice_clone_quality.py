"""Voice clone quality metrics and teacher acceptance workflow."""

from alembic import op
import sqlalchemy as sa

revision = "0034_voice_clone_quality"
down_revision = "0033_teacher_parent_threads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("teacher_voice_samples", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column("teacher_voice_samples", sa.Column("quality_tier", sa.String(32), nullable=True))
    op.add_column("teacher_voice_samples", sa.Column("clone_confidence", sa.Float(), nullable=True))
    op.add_column("teacher_voice_samples", sa.Column("transcript_quality", sa.Float(), nullable=True))
    op.add_column("teacher_voice_samples", sa.Column("noise_score", sa.Float(), nullable=True))
    op.add_column("teacher_voice_samples", sa.Column("speech_score", sa.Float(), nullable=True))
    op.add_column("teacher_voice_samples", sa.Column("preview_audio_path", sa.String(1024), nullable=True))
    op.add_column(
        "teacher_voice_samples",
        sa.Column("teacher_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("teacher_voice_samples", sa.Column("quality_details_json", sa.Text(), nullable=True))

    # Legacy ready rows without metrics are not production-safe — require re-review
    op.execute(
        sa.text(
            """
            UPDATE teacher_voice_samples
            SET processing_status = 'awaiting_acceptance',
                teacher_accepted = false
            WHERE processing_status = 'ready'
              AND quality_score IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_column("teacher_voice_samples", "quality_details_json")
    op.drop_column("teacher_voice_samples", "teacher_accepted")
    op.drop_column("teacher_voice_samples", "preview_audio_path")
    op.drop_column("teacher_voice_samples", "speech_score")
    op.drop_column("teacher_voice_samples", "noise_score")
    op.drop_column("teacher_voice_samples", "transcript_quality")
    op.drop_column("teacher_voice_samples", "clone_confidence")
    op.drop_column("teacher_voice_samples", "quality_tier")
    op.drop_column("teacher_voice_samples", "quality_score")
