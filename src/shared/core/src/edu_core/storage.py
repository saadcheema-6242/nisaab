"""File storage: Google Cloud Storage (production) or Supabase Storage (local dev).

Documents are kept in one private bucket:
- ``{project_id}/{document_id}.{ext}``: the original upload
- ``{project_id}/{document_id}.contents.txt``: the extracted markdown text

``create_storage`` picks the backend from the ``STORAGE_BACKEND`` setting.
"""

from datetime import timedelta
from urllib.parse import quote

import httpx

DEFAULT_TIMEOUT_SECONDS = 120


class StorageError(RuntimeError):
    """Raised when a storage request fails."""


def create_storage(
    backend: str,
    bucket: str,
    supabase_url: str = "",
    supabase_service_role_key: str = "",
) -> "StorageService | GCSStorageService":
    """Create the storage client for ``backend`` (``gcs`` or ``supabase``)."""
    if backend.strip().lower() == "gcs":
        return GCSStorageService(bucket)
    return StorageService(supabase_url, supabase_service_role_key, bucket)


class GCSStorageService:
    """Google Cloud Storage client with the same interface as ``StorageService``.

    Uses Application Default Credentials (the Cloud Run service account). Signed
    URLs are signed through the IAM API, so the service account needs the
    Service Account Token Creator role on itself.
    """

    def __init__(self, bucket: str):
        from google.cloud import storage

        if not bucket:
            raise StorageError("STORAGE_BUCKET must be set")
        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket)
        self.bucket = bucket

    def ensure_bucket(self) -> None:
        """Check that the bucket is reachable (deploy/gcp/deploy.sh creates it).

        Lists at most one object, which only needs the object-level access the
        service account has (bucket metadata would need more).
        """
        from google.api_core.exceptions import NotFound

        try:
            next(iter(self._client.list_blobs(self.bucket, max_results=1)), None)
        except NotFound as e:
            raise StorageError(f"Bucket {self.bucket} does not exist") from e

    def upload(
        self, path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        """Upload (or overwrite) an object."""
        self._bucket.blob(path).upload_from_string(data, content_type=content_type)

    def download(self, path: str) -> bytes:
        """Download an object's bytes."""
        return self._bucket.blob(path).download_as_bytes()

    def delete(self, paths: list[str]) -> None:
        """Delete objects (missing objects are ignored)."""
        from google.api_core.exceptions import NotFound

        for path in paths:
            try:
                self._bucket.blob(path).delete()
            except NotFound:
                pass

    def list_paths(self, prefix: str) -> list[str]:
        """List object paths under a folder prefix (e.g. a project ID)."""
        folder = prefix.rstrip("/") + "/"
        return [blob.name for blob in self._client.list_blobs(self.bucket, prefix=folder)]

    def signed_url(
        self, path: str, expires_in: int = 3600, download: bool = False
    ) -> str:
        """Create a temporary URL that lets a browser read the object."""
        import google.auth
        from google.auth.transport.requests import Request

        credentials, _ = google.auth.default()
        kwargs: dict = {}
        if not (getattr(credentials, "signer_email", None) and hasattr(credentials, "sign_bytes")):
            # Cloud Run credentials have no private key: sign through the IAM API.
            # The real service account email is only known after a refresh.
            credentials.refresh(Request())
            email = getattr(credentials, "service_account_email", None)
            if not email or email == "default":
                raise StorageError("Signed URLs need service account credentials")
            kwargs = {"service_account_email": email, "access_token": credentials.token}
        if download:
            kwargs["response_disposition"] = "attachment"
        return self._bucket.blob(path).generate_signed_url(
            version="v4", expiration=timedelta(seconds=expires_in), method="GET", **kwargs
        )


class StorageService:
    """Small client for Supabase Storage using the service role key."""

    def __init__(self, supabase_url: str, service_role_key: str, bucket: str):
        """Initialize the storage client.

        Args:
            supabase_url: Supabase project URL (e.g. http://127.0.0.1:54321)
            service_role_key: Service role (secret) key; never expose it to browsers
            bucket: Bucket name for documents
        """
        if not supabase_url or not service_role_key:
            raise StorageError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        self.base_url = f"{supabase_url.rstrip('/')}/storage/v1"
        self.bucket = bucket
        self._headers = {"apikey": service_role_key}
        # Legacy JWT keys are also sent as a bearer token; new sb_secret_ keys
        # are only accepted in the apikey header.
        if service_role_key.startswith("eyJ"):
            self._headers["Authorization"] = f"Bearer {service_role_key}"

    def _url(self, *parts: str) -> str:
        return "/".join([self.base_url, *parts])

    def _object_path(self, path: str) -> str:
        return f"{quote(self.bucket)}/{quote(path)}"

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        response = httpx.request(
            method,
            url,
            headers={**self._headers, **kwargs.pop("headers", {})},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            **kwargs,
        )
        if response.status_code >= 400:
            raise StorageError(
                f"Storage {method} {url} failed ({response.status_code}): {response.text[:300]}"
            )
        return response

    def ensure_bucket(self) -> None:
        """Create the private bucket if it does not exist yet."""
        response = httpx.get(
            self._url("bucket", quote(self.bucket)),
            headers=self._headers,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return
        self._request(
            "POST",
            self._url("bucket"),
            json={"id": self.bucket, "name": self.bucket, "public": False},
        )

    def upload(
        self, path: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        """Upload (or overwrite) an object."""
        self._request(
            "POST",
            self._url("object", self._object_path(path)),
            content=data,
            headers={"Content-Type": content_type, "x-upsert": "true"},
        )

    def download(self, path: str) -> bytes:
        """Download an object's bytes."""
        return self._request(
            "GET", self._url("object", self._object_path(path))
        ).content

    def delete(self, paths: list[str]) -> None:
        """Delete objects (missing objects are ignored)."""
        if paths:
            self._request(
                "DELETE", self._url("object", quote(self.bucket)), json={"prefixes": paths}
            )

    def list_paths(self, prefix: str) -> list[str]:
        """List object paths directly under a folder prefix (e.g. a project ID)."""
        items = self._request(
            "POST",
            self._url("object", "list", quote(self.bucket)),
            json={"prefix": prefix, "limit": 1000},
        ).json()
        return [f"{prefix.rstrip('/')}/{item['name']}" for item in items if item.get("id")]

    def signed_url(
        self, path: str, expires_in: int = 3600, download: bool = False
    ) -> str:
        """Create a temporary URL that lets a browser read the object."""
        signed = self._request(
            "POST",
            self._url("object", "sign", self._object_path(path)),
            json={"expiresIn": expires_in},
        ).json()["signedURL"]
        url = f"{self.base_url}{signed}"
        return f"{url}&download" if download else url


def document_path(project_id: str, document_id: str, file_type: str) -> str:
    """Storage path of an uploaded document."""
    if file_type and file_type != "unknown":
        return f"{project_id}/{document_id}.{file_type}"
    return f"{project_id}/{document_id}"


def document_contents_path(project_id: str, document_id: str) -> str:
    """Storage path of a document's extracted markdown text."""
    return f"{project_id}/{document_id}.contents.txt"
