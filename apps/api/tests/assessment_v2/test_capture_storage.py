from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
import json

import httpx
import pytest

from app.assessment_v2.storage import (
    StorageInputError,
    StorageUnavailableError,
    SupabasePrivateStorageAdapter,
)
from app.core.config import Settings


SERVICE_ROLE_KEY = "synthetic-service-role-key"
OPAQUE_OBJECT_KEY = "tenant-opaque/assessment-opaque/capture-opaque"
TUS_ENDPOINT = "https://project-ref.supabase.co/storage/v1/upload/resumable"
DIRECT_STORAGE_TUS_ENDPOINT = "https://project-ref.storage.supabase.co/storage/v1/upload/resumable"
UNRELATED_TUS_ENDPOINT = "https://other-project.supabase.co/storage/v1/upload/resumable"
DIRECT_SIGNED_DOWNLOAD_URL = (
    "https://project-ref.storage.supabase.co/storage/v1/object/sign/"
    "capture-private/tenant-opaque/assessment-opaque/capture-opaque?token=synthetic-download-token"
)
UNRELATED_SIGNED_DOWNLOAD_URL = (
    "https://other-project.supabase.co/storage/v1/object/sign/"
    "capture-private/tenant-opaque/assessment-opaque/capture-opaque?token=synthetic-download-token"
)
CAPTURE_HARD_MAX_BYTES = 250 * 1024 * 1024


@dataclass
class FakeSdkResponse:
    data: object
    error: object | None = None


class FailingModelDump:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def model_dump(self) -> object:
        raise self.error


class FailingMapping(dict[str, object]):
    def get(self, key: str, default: object = None) -> object:
        del key, default
        raise KeyError("synthetic provider response shape")


class FakeBucket:
    def __init__(self) -> None:
        self.create_signed_upload_url_calls: list[tuple[str, object]] = []
        self.create_signed_url_calls: list[tuple[str, int]] = []
        self.info_calls: list[str] = []
        self.remove_calls: list[list[str]] = []
        self.public_url_calls = 0
        self.signed_upload_response: object = {
            "signed_url": "https://project-ref.supabase.co/storage/v1/object/upload/sign/capture-private/token",
            "token": "synthetic-upload-signature",
        }
        self.signed_download_response: object = FakeSdkResponse(
            data={
                "signedURL": "https://project-ref.supabase.co/storage/v1/object/sign/"
                "capture-private/tenant-opaque/assessment-opaque/capture-opaque?token=synthetic-download-token"
            }
        )
        self.info_response: object = FakeSdkResponse(
            data={
                "metadata": {
                    "mimetype": "audio/webm",
                    "size": "456",
                    "eTag": '"0123456789abcdef"',
                    "checksum": "sha256:0123456789abcdef",
                }
            }
        )
        self.remove_response: object = [{"name": OPAQUE_OBJECT_KEY}]
        self.raise_on: dict[str, Exception] = {}

    def create_signed_upload_url(self, path: str, options: object) -> object:
        self.create_signed_upload_url_calls.append((path, options))
        self._raise_if_requested("create_signed_upload_url")
        return self.signed_upload_response

    def create_signed_url(self, path: str, expires_in: int) -> object:
        self.create_signed_url_calls.append((path, expires_in))
        self._raise_if_requested("create_signed_url")
        return self.signed_download_response

    def info(self, path: str) -> object:
        self.info_calls.append(path)
        self._raise_if_requested("info")
        return self.info_response

    def remove(self, paths: list[str]) -> object:
        self.remove_calls.append(paths)
        self._raise_if_requested("remove")
        return self.remove_response

    def get_public_url(self, path: str) -> str:
        del path
        self.public_url_calls += 1
        return "https://project-ref.supabase.co/storage/v1/object/public/capture-private/unreachable"

    def _raise_if_requested(self, operation: str) -> None:
        if exception := self.raise_on.get(operation):
            raise exception


class FakeStorageClient:
    def __init__(self, bucket: FakeBucket) -> None:
        self.bucket = bucket
        self.requested_buckets: list[str] = []

    def from_(self, bucket_name: str) -> FakeBucket:
        self.requested_buckets.append(bucket_name)
        return self.bucket


class FakeSupabaseClient:
    def __init__(self, bucket: FakeBucket) -> None:
        self.storage = FakeStorageClient(bucket)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "storage_mode": "supabase_private",
        "supabase_storage_url": "https://project-ref.supabase.co",
        "supabase_storage_service_role_key": SERVICE_ROLE_KEY,
        "supabase_storage_bucket": "capture-private",
        "supabase_storage_tus_endpoint": TUS_ENDPOINT,
    }
    values.update(overrides)
    return Settings(**values)


def _adapter(bucket: FakeBucket, **settings_overrides: object) -> SupabasePrivateStorageAdapter:
    return SupabasePrivateStorageAdapter(
        settings=_settings(**settings_overrides),
        client=FakeSupabaseClient(bucket),
        now=lambda: datetime(2026, 9, 6, 10, 30, tzinfo=UTC),
    )


def test_create_signed_upload_grant_uses_private_tus_contract_without_service_key_exposure() -> None:
    bucket = FakeBucket()

    grant = _adapter(bucket).create_signed_upload_grant(
        object_key=OPAQUE_OBJECT_KEY,
        content_type="audio/webm",
        declared_size_bytes=456,
    )

    assert grant.tus_endpoint == TUS_ENDPOINT
    assert grant.headers["x-signature"] == "synthetic-upload-signature"
    assert grant.headers["Upload-Metadata"] == ",".join(
        (
            "bucketName " + base64.b64encode(b"capture-private").decode("ascii"),
            "objectName " + base64.b64encode(OPAQUE_OBJECT_KEY.encode("utf-8")).decode("ascii"),
            "contentType " + base64.b64encode(b"audio/webm").decode("ascii"),
        )
    )
    assert grant.upload_metadata == {
        "bucketName": "capture-private",
        "objectName": OPAQUE_OBJECT_KEY,
        "contentType": "audio/webm",
    }
    assert grant.bucket == "capture-private"
    assert grant.object_key == OPAQUE_OBJECT_KEY
    assert grant.content_type == "audio/webm"
    assert grant.upsert is False
    assert grant.chunk_size_bytes == 6 * 1024 * 1024
    assert grant.expires_in_seconds == 7200
    assert grant.expires_at == datetime(2026, 9, 6, 12, 30, tzinfo=UTC)
    assert bucket.create_signed_upload_url_calls[0][0] == OPAQUE_OBJECT_KEY
    upload_options = bucket.create_signed_upload_url_calls[0][1]
    assert upload_options.upsert == "false"
    assert not isinstance(upload_options, dict)
    assert SERVICE_ROLE_KEY not in repr(grant)
    assert not hasattr(grant, "filename")


@pytest.mark.parametrize(
    ("object_key", "content_type", "declared_size_bytes"),
    (
        ("", "audio/webm", 1),
        ("../not-opaque", "audio/webm", 1),
        (OPAQUE_OBJECT_KEY, "", 1),
        (OPAQUE_OBJECT_KEY, "not-a-media-type", 1),
        (OPAQUE_OBJECT_KEY, "audio/webm", 0),
        (OPAQUE_OBJECT_KEY, "audio/webm", CAPTURE_HARD_MAX_BYTES + 1),
    ),
)
def test_invalid_upload_input_is_rejected_before_client_construction(
    object_key: str,
    content_type: str,
    declared_size_bytes: int,
) -> None:
    factory_calls: list[tuple[str, str]] = []

    def factory(url: str, service_role_key: str) -> object:
        factory_calls.append((url, service_role_key))
        return FakeSupabaseClient(FakeBucket())

    adapter = SupabasePrivateStorageAdapter(settings=_settings(), client_factory=factory)

    with pytest.raises(StorageInputError):
        adapter.create_signed_upload_grant(
            object_key=object_key,
            content_type=content_type,
            declared_size_bytes=declared_size_bytes,
        )

    assert factory_calls == []


@pytest.mark.parametrize(
    "content_type",
    (
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
    ),
)
def test_create_signed_upload_grant_accepts_only_explicit_capture_mime_families(content_type: str) -> None:
    bucket = FakeBucket()

    grant = _adapter(bucket).create_signed_upload_grant(
        object_key=OPAQUE_OBJECT_KEY,
        content_type=content_type,
        declared_size_bytes=456,
    )

    assert grant.content_type == content_type


@pytest.mark.parametrize("content_type", ("application/octet-stream", "audio/flac", "text/plain", "video/webm"))
def test_create_signed_upload_grant_rejects_unapproved_capture_mime_before_provider_call(
    content_type: str,
) -> None:
    bucket = FakeBucket()

    with pytest.raises(StorageInputError):
        _adapter(bucket).create_signed_upload_grant(
            object_key=OPAQUE_OBJECT_KEY,
            content_type=content_type,
            declared_size_bytes=456,
        )

    assert bucket.create_signed_upload_url_calls == []


def test_create_signed_upload_grant_rejects_unrelated_tus_project_before_provider_call() -> None:
    bucket = FakeBucket()

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket, supabase_storage_tus_endpoint=UNRELATED_TUS_ENDPOINT).create_signed_upload_grant(
            object_key=OPAQUE_OBJECT_KEY,
            content_type="audio/webm",
            declared_size_bytes=456,
        )

    assert raised.value.code == "storage_unavailable"
    assert bucket.create_signed_upload_url_calls == []


def test_create_signed_upload_grant_rejects_unapproved_storage_url_before_client_construction() -> None:
    factory_calls: list[tuple[str, str]] = []

    def factory(url: str, service_role_key: str) -> object:
        factory_calls.append((url, service_role_key))
        return FakeSupabaseClient(FakeBucket())

    adapter = SupabasePrivateStorageAdapter(
        settings=_settings(
            supabase_storage_url="https://attacker.example",
            supabase_storage_tus_endpoint="https://attacker.example/storage/v1/upload/resumable",
        ),
        client_factory=factory,
    )

    with pytest.raises(StorageUnavailableError) as raised:
        adapter.create_signed_upload_grant(
            object_key=OPAQUE_OBJECT_KEY,
            content_type="audio/webm",
            declared_size_bytes=456,
        )

    assert raised.value.code == "storage_unavailable"
    assert factory_calls == []


def test_create_signed_upload_grant_accepts_supabase_direct_storage_tus_hostname() -> None:
    bucket = FakeBucket()

    grant = _adapter(bucket, supabase_storage_tus_endpoint=DIRECT_STORAGE_TUS_ENDPOINT).create_signed_upload_grant(
        object_key=OPAQUE_OBJECT_KEY,
        content_type="audio/webm",
        declared_size_bytes=456,
    )

    assert grant.tus_endpoint == DIRECT_STORAGE_TUS_ENDPOINT


def test_create_signed_upload_grant_rejects_a_provider_attribute_error_as_storage_unavailable() -> None:
    bucket = FakeBucket()
    bucket.raise_on["create_signed_upload_url"] = AttributeError(
        f"SDK failed for {OPAQUE_OBJECT_KEY} with {SERVICE_ROLE_KEY}"
    )

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket).create_signed_upload_grant(
            object_key=OPAQUE_OBJECT_KEY,
            content_type="audio/webm",
            declared_size_bytes=456,
        )

    assert raised.value.code == "storage_unavailable"
    assert OPAQUE_OBJECT_KEY not in str(raised.value)
    assert SERVICE_ROLE_KEY not in str(raised.value)
    assert raised.value.__cause__ is None


@pytest.mark.parametrize("configured_maximum", (0, -1, CAPTURE_HARD_MAX_BYTES + 1))
def test_create_signed_upload_grant_rejects_an_invalid_configured_capture_ceiling(
    configured_maximum: int,
) -> None:
    bucket = FakeBucket()

    with pytest.raises(StorageUnavailableError):
        _adapter(bucket, capture_max_upload_size_bytes=configured_maximum).create_signed_upload_grant(
            object_key=OPAQUE_OBJECT_KEY,
            content_type="audio/webm",
            declared_size_bytes=456,
        )

    assert bucket.create_signed_upload_url_calls == []


def test_create_signed_download_grant_uses_private_signed_url_not_public_url() -> None:
    bucket = FakeBucket()

    grant = _adapter(bucket).create_signed_download_grant(OPAQUE_OBJECT_KEY)

    assert grant.url.startswith("https://project-ref.supabase.co/storage/v1/object/sign/")
    assert "/public/" not in grant.url
    assert grant.expires_in_seconds == 900
    assert grant.expires_at == datetime(2026, 9, 6, 10, 45, tzinfo=UTC)
    assert bucket.create_signed_url_calls == [(OPAQUE_OBJECT_KEY, 900)]
    assert bucket.public_url_calls == 0


def test_create_signed_download_grant_accepts_the_direct_storage_host() -> None:
    bucket = FakeBucket()
    bucket.signed_download_response = FakeSdkResponse(data={"signedURL": DIRECT_SIGNED_DOWNLOAD_URL})

    grant = _adapter(bucket).create_signed_download_grant(OPAQUE_OBJECT_KEY)

    assert grant.url == DIRECT_SIGNED_DOWNLOAD_URL


def test_create_signed_download_grant_rejects_an_unrelated_host() -> None:
    bucket = FakeBucket()
    bucket.signed_download_response = FakeSdkResponse(data={"signedURL": UNRELATED_SIGNED_DOWNLOAD_URL})

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket).create_signed_download_grant(OPAQUE_OBJECT_KEY)

    assert raised.value.code == "storage_unavailable"
    assert OPAQUE_OBJECT_KEY not in str(raised.value)


def test_create_signed_download_grant_rejects_a_public_url_response() -> None:
    bucket = FakeBucket()
    bucket.signed_download_response = {
        "signedURL": "https://project-ref.supabase.co/storage/v1/object/public/capture-private/opaque"
    }

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket).create_signed_download_grant(OPAQUE_OBJECT_KEY)

    assert raised.value.code == "storage_unavailable"
    assert OPAQUE_OBJECT_KEY not in str(raised.value)
    assert bucket.public_url_calls == 0


def test_get_object_metadata_normalizes_sdk_data_without_echoing_the_object_key() -> None:
    bucket = FakeBucket()

    metadata = _adapter(bucket).get_object_metadata(OPAQUE_OBJECT_KEY)

    assert metadata.content_type == "audio/webm"
    assert metadata.size_bytes == 456
    assert metadata.etag == "0123456789abcdef"
    assert metadata.checksum == "sha256:0123456789abcdef"
    assert bucket.info_calls == [OPAQUE_OBJECT_KEY]
    assert OPAQUE_OBJECT_KEY not in repr(metadata)


@pytest.mark.parametrize(
    "provider_metadata",
    (
        {"size": "456"},
        {"mimetype": "audio/webm"},
        {"mimetype": "application/octet-stream", "size": "456"},
        {"mimetype": "audio/webm", "size": "not-a-size"},
        {"mimetype": "audio/webm", "size": -1},
        {"mimetype": "audio/webm", "size": CAPTURE_HARD_MAX_BYTES + 1},
    ),
)
def test_get_object_metadata_fails_closed_without_valid_authoritative_type_and_size(
    provider_metadata: dict[str, object],
) -> None:
    bucket = FakeBucket()
    bucket.info_response = FakeSdkResponse(data={"metadata": provider_metadata})

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket).get_object_metadata(OPAQUE_OBJECT_KEY)

    assert raised.value.code == "storage_unavailable"
    assert OPAQUE_OBJECT_KEY not in str(raised.value)


@pytest.mark.parametrize(
    "provider_error",
    (
        AttributeError("synthetic SDK attribute failure"),
        KeyError("synthetic provider key"),
        TypeError("synthetic provider type failure"),
        ValueError("synthetic provider value failure"),
        json.JSONDecodeError("synthetic provider JSON failure", "{}", 0),
    ),
)
def test_provider_boundary_maps_sdk_and_parse_exceptions_to_bare_storage_unavailable(
    provider_error: Exception,
) -> None:
    bucket = FakeBucket()
    bucket.raise_on["info"] = provider_error

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket).get_object_metadata(OPAQUE_OBJECT_KEY)

    assert raised.value.code == "storage_unavailable"
    assert str(raised.value) == "storage_unavailable"
    assert raised.value.__cause__ is None


@pytest.mark.parametrize(
    "provider_response",
    (
        FailingModelDump(ValueError("synthetic model dump failure")),
        FailingModelDump(TypeError("synthetic model dump type failure")),
        FailingModelDump(json.JSONDecodeError("synthetic model dump JSON failure", "{}", 0)),
        FakeSdkResponse(data=FailingMapping()),
    ),
)
def test_malformed_sdk_metadata_shapes_fail_closed_without_provider_details(
    provider_response: object,
) -> None:
    bucket = FakeBucket()
    bucket.info_response = FakeSdkResponse(data=provider_response)

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket).get_object_metadata(OPAQUE_OBJECT_KEY)

    assert raised.value.code == "storage_unavailable"
    assert str(raised.value) == "storage_unavailable"
    assert raised.value.__cause__ is None


@pytest.mark.parametrize("configured_ttl", (7199, 7201))
def test_create_signed_upload_grant_rejects_a_non_provider_controlled_upload_ttl(
    configured_ttl: int,
) -> None:
    bucket = FakeBucket()

    with pytest.raises(StorageUnavailableError):
        _adapter(
            bucket,
            supabase_storage_signed_upload_ttl_seconds=configured_ttl,
        ).create_signed_upload_grant(
            object_key=OPAQUE_OBJECT_KEY,
            content_type="audio/webm",
            declared_size_bytes=456,
        )

    assert bucket.create_signed_upload_url_calls == []


def test_provider_failure_and_error_payload_fail_closed_without_provider_details() -> None:
    bucket = FakeBucket()
    bucket.raise_on["info"] = httpx.ConnectError(f"provider rejected {OPAQUE_OBJECT_KEY}")

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket).get_object_metadata(OPAQUE_OBJECT_KEY)

    assert raised.value.code == "storage_unavailable"
    assert str(raised.value) == "storage_unavailable"
    assert OPAQUE_OBJECT_KEY not in str(raised.value)
    assert raised.value.__cause__ is None

    bucket.raise_on.clear()
    bucket.info_response = FakeSdkResponse(data=None, error={"message": f"denied {OPAQUE_OBJECT_KEY}"})

    with pytest.raises(StorageUnavailableError) as payload_raised:
        _adapter(bucket).get_object_metadata(OPAQUE_OBJECT_KEY)

    assert payload_raised.value.code == "storage_unavailable"
    assert OPAQUE_OBJECT_KEY not in str(payload_raised.value)


def test_delete_object_targets_only_the_requested_object_and_confirms_deletion() -> None:
    bucket = FakeBucket()

    result = _adapter(bucket).delete_object(OPAQUE_OBJECT_KEY)

    assert result.deleted is True
    assert result.status == "deleted"
    assert bucket.remove_calls == [[OPAQUE_OBJECT_KEY]]


def test_delete_object_normalizes_a_successful_sdk_data_wrapper() -> None:
    bucket = FakeBucket()
    bucket.remove_response = FakeSdkResponse(data={"name": OPAQUE_OBJECT_KEY})

    result = _adapter(bucket).delete_object(OPAQUE_OBJECT_KEY)

    assert result.deleted is True
    assert result.status == "deleted"
    assert bucket.remove_calls == [[OPAQUE_OBJECT_KEY]]


def test_delete_object_fails_closed_when_provider_does_not_confirm_requested_object() -> None:
    bucket = FakeBucket()
    bucket.remove_response = FakeSdkResponse(data=[{"name": "different-opaque-object"}])

    with pytest.raises(StorageUnavailableError) as raised:
        _adapter(bucket).delete_object(OPAQUE_OBJECT_KEY)

    assert raised.value.code == "storage_unavailable"
    assert OPAQUE_OBJECT_KEY not in str(raised.value)
