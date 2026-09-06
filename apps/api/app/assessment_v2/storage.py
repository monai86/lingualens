"""Fail-closed private Supabase Storage access for future Capture V2 routes."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from importlib import import_module
import re
from typing import Protocol, TypeVar, cast
from urllib.parse import urlparse

import httpx

from app.core.config import MAX_CAPTURE_UPLOAD_SIZE_BYTES, Settings, get_settings


STORAGE_UNAVAILABLE = "storage_unavailable"
INVALID_STORAGE_REQUEST = "invalid_storage_request"
_MISSING = object()
_OBJECT_KEY_SEGMENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}")
_MEDIA_TYPE_RE = re.compile(
    r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(?:;\s*[A-Za-z0-9!#$&^_.+-]+=[A-Za-z0-9!#$&^_.+-]+)*"
)
CAPTURE_ALLOWED_MIME_TYPES = frozenset(
    {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
        "video/mp4",
        "video/quicktime",
        "audio/webm",
        "audio/webm;codecs=opus",
        "audio/ogg",
        "audio/ogg;codecs=opus",
        "audio/opus",
    }
)
_INTEGRITY_VALUE_RE = re.compile(r"[A-Za-z0-9._:-]{1,256}")
_T = TypeVar("_T")


class StorageUnavailableError(RuntimeError):
    """Raised when private Storage cannot safely complete an operation."""

    code = STORAGE_UNAVAILABLE

    def __init__(self) -> None:
        super().__init__(self.code)


class StorageInputError(ValueError):
    """Raised before any provider call for an invalid capture Storage request."""

    code = INVALID_STORAGE_REQUEST

    def __init__(self) -> None:
        super().__init__(self.code)


@dataclass(frozen=True)
class SignedUploadGrant:
    """Client-safe TUS upload details for one opaque private object."""

    tus_endpoint: str
    headers: Mapping[str, str]
    upload_metadata: Mapping[str, str]
    bucket: str
    object_key: str
    expires_at: datetime
    expires_in_seconds: int
    chunk_size_bytes: int
    content_type: str
    upsert: bool


@dataclass(frozen=True)
class SignedDownloadGrant:
    """A short-lived private download URL without object or credential echoes."""

    url: str
    expires_at: datetime
    expires_in_seconds: int


@dataclass(frozen=True)
class StorageObjectMetadata:
    """Safe normalized object attributes for later authoritative verification."""

    content_type: str | None
    size_bytes: int | None
    etag: str | None
    checksum: str | None


@dataclass(frozen=True)
class StorageDeletionResult:
    """Confirmed private-object deletion result."""

    deleted: bool
    status: str


@dataclass(frozen=True)
class _FallbackCreateSignedUploadUrlOptions:
    """Shape-compatible fallback for test environments without storage3."""

    upsert: str


class SupabaseBucket(Protocol):
    def create_signed_upload_url(self, path: str, options: object) -> object: ...

    def create_signed_url(self, path: str, expires_in: int) -> object: ...

    def info(self, path: str) -> object: ...

    def remove(self, paths: list[str]) -> object: ...


class SupabaseStorage(Protocol):
    def from_(self, bucket_name: str) -> SupabaseBucket: ...


class SupabaseClient(Protocol):
    storage: SupabaseStorage


SupabaseClientFactory = Callable[[str, str], SupabaseClient]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _provider_exception_types() -> tuple[type[BaseException], ...]:
    exception_types: list[type[BaseException]] = [AttributeError, httpx.HTTPError, OSError]
    try:
        from storage3.exceptions import StorageApiError, StorageException
    except ImportError:
        pass
    else:
        exception_types.extend((StorageApiError, StorageException))
    return tuple(exception_types)


def _call_provider(operation: Callable[[], _T]) -> _T:
    try:
        return operation()
    except _provider_exception_types():
        raise StorageUnavailableError() from None


def _create_default_client(url: str, service_role_key: str) -> SupabaseClient:
    try:
        supabase_module = import_module("supabase")
        create_client = getattr(supabase_module, "create_client")
    except (ImportError, AttributeError):
        raise StorageUnavailableError() from None
    return cast(SupabaseClient, _call_provider(lambda: create_client(url, service_role_key)))


def _create_signed_upload_options() -> object:
    """Create the pinned storage3 options object without an import-time dependency."""

    try:
        from storage3.types import CreateSignedUploadUrlOptions
    except ImportError:
        return _FallbackCreateSignedUploadUrlOptions(upsert="false")
    return CreateSignedUploadUrlOptions(upsert="false")


def _read_value(value: object, field_name: str) -> object:
    if isinstance(value, Mapping):
        return value.get(field_name, _MISSING)
    return getattr(value, field_name, _MISSING)


def _as_mapping(value: object) -> Mapping[str, object] | None:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    return None


def _unwrap_provider_response(response: object) -> object:
    error = _read_value(response, "error")
    if error is not _MISSING and error not in (None, "", False):
        raise StorageUnavailableError()
    data = _read_value(response, "data")
    return response if data is _MISSING else data


def _required_text(value: object, *field_names: str) -> str:
    for field_name in field_names:
        candidate = _read_value(value, field_name)
        if isinstance(candidate, str) and candidate and candidate == candidate.strip():
            return candidate
    raise StorageUnavailableError()


def _validate_object_key(object_key: str) -> str:
    if not isinstance(object_key, str) or not object_key or object_key != object_key.strip():
        raise StorageInputError()
    parts = object_key.split("/")
    if any(part in {"", ".", ".."} or _OBJECT_KEY_SEGMENT_RE.fullmatch(part) is None for part in parts):
        raise StorageInputError()
    return object_key


def _normalize_content_type(value: object) -> str | None:
    if not isinstance(value, str) or value != value.strip() or _MEDIA_TYPE_RE.fullmatch(value) is None:
        return None
    normalized = value.lower()
    return normalized if normalized in CAPTURE_ALLOWED_MIME_TYPES else None


def _validate_content_type(content_type: str) -> str:
    normalized = _normalize_content_type(content_type)
    if normalized is None:
        raise StorageInputError()
    return normalized


def _validate_declared_size(declared_size_bytes: int, maximum_size_bytes: int) -> int:
    if (
        not isinstance(declared_size_bytes, int)
        or isinstance(declared_size_bytes, bool)
        or declared_size_bytes <= 0
        or declared_size_bytes > maximum_size_bytes
    ):
        raise StorageInputError()
    return declared_size_bytes


def _format_upload_metadata(upload_metadata: Mapping[str, str]) -> str:
    return ",".join(
        f"{name} {base64.b64encode(value.encode('utf-8')).decode('ascii')}"
        for name, value in upload_metadata.items()
    )


def _is_private_signed_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and bool(parsed.query)
        and "/object/sign/" in parsed.path
        and "/object/public/" not in parsed.path
    )


def _normalize_size(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdecimal():
        normalized = int(value)
        return normalized if normalized > 0 else None
    return None


def _normalize_integrity_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().strip('"')
    if _INTEGRITY_VALUE_RE.fullmatch(normalized) is None:
        return None
    return normalized


def _first_normalized(
    sources: tuple[Mapping[str, object], ...],
    field_names: tuple[str, ...],
    normalizer: Callable[[object], _T | None],
) -> _T | None:
    for source in sources:
        for field_name in field_names:
            normalized = normalizer(source.get(field_name, _MISSING))
            if normalized is not None:
                return normalized
    return None


class CaptureStorageAdapter(Protocol):
    def create_signed_upload_grant(
        self,
        object_key: str,
        content_type: str,
        declared_size_bytes: int,
    ) -> SignedUploadGrant: ...

    def create_signed_download_grant(self, object_key: str) -> SignedDownloadGrant: ...

    def get_object_metadata(self, object_key: str) -> StorageObjectMetadata: ...

    def delete_object(self, object_key: str) -> StorageDeletionResult: ...


class SupabasePrivateStorageAdapter:
    """A lazy, injectable adapter over a configured private Supabase bucket."""

    storage_mode = "supabase_private"

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: SupabaseClient | None = None,
        client_factory: SupabaseClientFactory | None = None,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        if client is not None and client_factory is not None:
            raise ValueError("Specify a client or a client factory, not both.")
        self._settings = settings
        self._client = client
        self._client_factory = client_factory or _create_default_client
        self._now = now

    def create_signed_upload_grant(
        self,
        object_key: str,
        content_type: str,
        declared_size_bytes: int,
    ) -> SignedUploadGrant:
        object_key = _validate_object_key(object_key)
        content_type = _validate_content_type(content_type)
        settings = self._configured_settings()
        maximum_size_bytes = min(settings.capture_max_upload_size_bytes, MAX_CAPTURE_UPLOAD_SIZE_BYTES)
        _validate_declared_size(declared_size_bytes, maximum_size_bytes)

        response = _call_provider(
            lambda: self._bucket(settings).create_signed_upload_url(
                object_key,
                options=_create_signed_upload_options(),
            )
        )
        token = _required_text(_unwrap_provider_response(response), "token")
        upload_metadata = {
            "bucketName": settings.supabase_storage_bucket,
            "objectName": object_key,
            "contentType": content_type,
        }
        expires_at = self._expiry(settings.supabase_storage_signed_upload_ttl_seconds)
        return SignedUploadGrant(
            tus_endpoint=settings.supabase_storage_tus_endpoint,
            headers={
                "x-signature": token,
                "Upload-Metadata": _format_upload_metadata(upload_metadata),
            },
            upload_metadata=upload_metadata,
            bucket=settings.supabase_storage_bucket,
            object_key=object_key,
            expires_at=expires_at,
            expires_in_seconds=settings.supabase_storage_signed_upload_ttl_seconds,
            chunk_size_bytes=settings.supabase_storage_tus_chunk_size_bytes,
            content_type=content_type,
            upsert=False,
        )

    def create_signed_download_grant(self, object_key: str) -> SignedDownloadGrant:
        object_key = _validate_object_key(object_key)
        settings = self._configured_settings()
        response = _call_provider(
            lambda: self._bucket(settings).create_signed_url(
                object_key,
                settings.supabase_storage_signed_download_ttl_seconds,
            )
        )
        url = _required_text(_unwrap_provider_response(response), "signedURL", "signedUrl", "signed_url")
        if not _is_private_signed_url(url):
            raise StorageUnavailableError()
        return SignedDownloadGrant(
            url=url,
            expires_at=self._expiry(settings.supabase_storage_signed_download_ttl_seconds),
            expires_in_seconds=settings.supabase_storage_signed_download_ttl_seconds,
        )

    def get_object_metadata(self, object_key: str) -> StorageObjectMetadata:
        object_key = _validate_object_key(object_key)
        settings = self._configured_settings()
        payload = _unwrap_provider_response(_call_provider(lambda: self._bucket(settings).info(object_key)))
        object_info = _as_mapping(payload)
        if not object_info:
            raise StorageUnavailableError()
        provider_metadata = _as_mapping(object_info.get("metadata"))
        sources = (object_info,) if provider_metadata is None else (object_info, provider_metadata)
        content_type = _first_normalized(
            sources,
            ("content_type", "contentType", "mimetype", "mimeType"),
            _normalize_content_type,
        )
        size_bytes = _first_normalized(
            sources,
            ("size_bytes", "sizeBytes", "size"),
            _normalize_size,
        )
        if content_type is None or size_bytes is None:
            raise StorageUnavailableError()
        return StorageObjectMetadata(
            content_type=content_type,
            size_bytes=size_bytes,
            etag=_first_normalized(
                sources,
                ("etag", "eTag", "ETag"),
                _normalize_integrity_value,
            ),
            checksum=_first_normalized(
                sources,
                ("checksum", "checksum_sha256", "sha256"),
                _normalize_integrity_value,
            ),
        )

    def delete_object(self, object_key: str) -> StorageDeletionResult:
        object_key = _validate_object_key(object_key)
        settings = self._configured_settings()
        response = _unwrap_provider_response(_call_provider(lambda: self._bucket(settings).remove([object_key])))
        deleted_objects = response if isinstance(response, list) else [response]
        if len(deleted_objects) != 1:
            raise StorageUnavailableError()
        deleted_object = _as_mapping(deleted_objects[0])
        if deleted_object is None or deleted_object.get("name") != object_key:
            raise StorageUnavailableError()
        return StorageDeletionResult(deleted=True, status="deleted")

    def _configured_settings(self) -> Settings:
        settings = self._settings or get_settings()
        if not settings.has_valid_supabase_private_storage_configuration:
            raise StorageUnavailableError()
        return settings

    def _bucket(self, settings: Settings) -> SupabaseBucket:
        client = self._client
        if client is None:
            client = self._client_factory(
                settings.supabase_storage_url,
                settings.supabase_storage_service_role_key,
            )
            if client is None:
                raise StorageUnavailableError()
            self._client = client
        return _call_provider(lambda: client.storage.from_(settings.supabase_storage_bucket))

    def _expiry(self, expires_in_seconds: int) -> datetime:
        now = self._now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return now + timedelta(seconds=expires_in_seconds)
