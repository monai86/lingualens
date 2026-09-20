"""Legacy clinical workflow repository compatibility surface.

NOTICE: This module is retained strictly for backward compatibility with research
pilot tests and legacy workflows. For production development, use canonical
repositories in `apps.api.app.repositories`. See `src/clinical_workflow/README.md`
and `docs/PROJECT_SOURCE_OF_TRUTH.md`.
"""

from .repository_interface import ClinicalRepository
from .mock_repository import MockClinicalRepository
from .postgres_supabase_repository import PostgresSupabaseRepository
from .models import (
    ALLOWED_AUDIO_FILE_TYPES,
    ALLOWED_TRANSCRIPT_FILE_TYPES,
    ClinicalSignoff,
    ConsentRecord,
    FileObject,
    ModelRun,
    MAX_AUDIO_FILE_SIZE_BYTES,
    MAX_AUDIO_FILE_SIZE_MB,
    MOCK_MODE,
    ProcessingJob,
    SAFETY_DISCLAIMER,
    TranscriptLine,
)

__all__ = [
    "ClinicalRepository",
    "MockClinicalRepository",
    "PostgresSupabaseRepository",
    "ALLOWED_AUDIO_FILE_TYPES",
    "ALLOWED_TRANSCRIPT_FILE_TYPES",
    "ClinicalSignoff",
    "ConsentRecord",
    "FileObject",
    "ModelRun",
    "MAX_AUDIO_FILE_SIZE_BYTES",
    "MAX_AUDIO_FILE_SIZE_MB",
    "MOCK_MODE",
    "ProcessingJob",
    "SAFETY_DISCLAIMER",
    "TranscriptLine",
]
