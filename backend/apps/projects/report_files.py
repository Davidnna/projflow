import io
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path

from django.core.exceptions import ValidationError

MAX_REPORT_DOCUMENT_BYTES = 20 * 1024 * 1024
SIGNED_URL_TTL_SECONDS = 300

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
logger = logging.getLogger(__name__)


class ReportStorageError(Exception):
    pass


def _safe_original_filename(value):
    filename = str(value or "document").replace("\\", "/").split("/")[-1].strip()
    filename = re.sub(r"[^A-Za-z0-9._() -]", "_", filename)
    return (filename or "document")[:255]


def inspect_report_document(uploaded_file):
    filename = _safe_original_filename(uploaded_file.name)
    extension = Path(filename).suffix.lower()
    if extension not in {".pdf", ".docx"}:
        raise ValidationError("Upload the report section as a PDF or DOCX document.")
    if uploaded_file.size <= 0:
        raise ValidationError("The selected document is empty.")
    if uploaded_file.size > MAX_REPORT_DOCUMENT_BYTES:
        raise ValidationError("Each report document must not exceed 20 MB.")

    try:
        content = uploaded_file.read(MAX_REPORT_DOCUMENT_BYTES + 1)
    finally:
        uploaded_file.seek(0)

    if len(content) > MAX_REPORT_DOCUMENT_BYTES:
        raise ValidationError("Each report document must not exceed 20 MB.")

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValidationError("The selected file is not a valid PDF document.")
        content_type = PDF_CONTENT_TYPE
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise ValidationError("The selected file is not a valid DOCX document.")
                if sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024:
                    raise ValidationError("The selected DOCX document contains too much expanded data.")
                if archive.testzip() is not None:
                    raise ValidationError("The selected DOCX document is damaged. Save it again and retry.")
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            raise ValidationError("The selected file is not a valid DOCX document.") from exc
        content_type = DOCX_CONTENT_TYPE

    return {
        "original_filename": filename,
        "file_size": len(content),
        "content_type": content_type,
    }


def read_report_document(uploaded_file):
    content = uploaded_file.read(MAX_REPORT_DOCUMENT_BYTES + 1)
    uploaded_file.seek(0)
    if len(content) > MAX_REPORT_DOCUMENT_BYTES:
        raise ValidationError("Each report document must not exceed 20 MB.")
    metadata = inspect_report_document(uploaded_file)
    return content, metadata


def _storage_configuration():
    base_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    legacy_service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    api_key = secret_key or legacy_service_role_key
    bucket = os.environ.get("PROJFLOW_REPORTS_BUCKET", "projflow-project-reports").strip()
    missing = []
    if not base_url:
        missing.append("SUPABASE_URL")
    if not api_key:
        missing.append("SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY")
    if not bucket:
        missing.append("PROJFLOW_REPORTS_BUCKET")
    if missing:
        logger.error(
            "Private report storage configuration is incomplete; missing: %s",
            ", ".join(missing),
        )
        raise ReportStorageError("Private document storage is not configured.")
    if secret_key and legacy_service_role_key:
        logger.warning(
            "Both Supabase storage key variables are configured; SUPABASE_SECRET_KEY takes precedence."
        )
    return base_url, api_key, bucket


def _encoded_path(value):
    return "/".join(urllib.parse.quote(part, safe="") for part in str(value).split("/"))


def _storage_request(method, endpoint, payload=None, content_type=None):
    base_url, api_key, _ = _storage_configuration()
    key_source = (
        "SUPABASE_SECRET_KEY"
        if os.environ.get("SUPABASE_SECRET_KEY", "").strip()
        else "SUPABASE_SERVICE_ROLE_KEY"
    )
    route = endpoint.lstrip("/").split("/", 1)[0] or "unknown"
    headers = {"apikey": api_key}
    if not api_key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {api_key}"
    if isinstance(payload, bytes):
        body = payload
        headers["Content-Type"] = content_type or "application/octet-stream"
    elif payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        body = None
    request = urllib.request.Request(
        f"{base_url}/storage/v1/{endpoint.lstrip('/')}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            response_body = response.read()
            if not response_body:
                return {}
            try:
                return json.loads(response_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}
    except urllib.error.HTTPError as exc:
        response_body = b""
        try:
            response_body = exc.read(4096)
        except OSError:
            pass
        error_code = "unknown"
        error_message = "No response details returned"
        try:
            error_payload = json.loads(response_body.decode("utf-8"))
            if isinstance(error_payload, dict):
                error_code = str(
                    error_payload.get("code")
                    or error_payload.get("error")
                    or error_payload.get("error_code")
                    or "unknown"
                )[:100]
                error_message = str(
                    error_payload.get("message")
                    or error_payload.get("msg")
                    or error_payload.get("error_description")
                    or error_payload.get("error")
                    or error_message
                )[:300]
        except (UnicodeDecodeError, json.JSONDecodeError):
            if response_body:
                error_message = response_body.decode("utf-8", errors="replace")[:300]
        # Never log credentials, authorization headers, or uploaded document contents.
        for sensitive_value in (api_key,):
            if sensitive_value:
                error_message = error_message.replace(sensitive_value, "[REDACTED]")
        logger.error(
            "Supabase Storage request failed: method=%s route=%s status=%s code=%s message=%s key_source=%s",
            method,
            route,
            exc.code,
            error_code,
            error_message,
            key_source,
        )
        raise ReportStorageError("The document service could not complete the request.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        logger.error(
            "Supabase Storage network request failed: method=%s route=%s reason_type=%s key_source=%s",
            method,
            route,
            type(reason).__name__,
            key_source,
        )
        raise ReportStorageError("The document service is temporarily unavailable.") from exc


def _assert_private_bucket(bucket):
    details = _storage_request("GET", f"bucket/{urllib.parse.quote(bucket, safe='')}")
    if details.get("public") is not False:
        logger.error(
            "Supabase report bucket privacy check failed: bucket_public_value=%r metadata_contains_public=%s",
            details.get("public"),
            "public" in details,
        )
        raise ReportStorageError("The project report storage bucket must be private.")


def upload_report_document(*, object_path, content, content_type):
    _, _, bucket = _storage_configuration()
    _assert_private_bucket(bucket)
    endpoint = f"object/{urllib.parse.quote(bucket, safe='')}/{_encoded_path(object_path)}"
    _storage_request(
        "POST",
        endpoint,
        payload=content,
        content_type=content_type,
    )
    return object_path


def remove_report_document(object_path):
    try:
        _, _, bucket = _storage_configuration()
        endpoint = f"object/{urllib.parse.quote(bucket, safe='')}/{_encoded_path(object_path)}"
        _storage_request("DELETE", endpoint)
    except ReportStorageError:
        return


def create_report_download_url(object_path):
    _, _, bucket = _storage_configuration()
    _assert_private_bucket(bucket)
    endpoint = f"object/sign/{urllib.parse.quote(bucket, safe='')}/{_encoded_path(object_path)}"
    result = _storage_request(
        "POST",
        endpoint,
        payload={"expiresIn": SIGNED_URL_TTL_SECONDS},
    )
    signed_url = result.get("signedURL") or result.get("signedUrl")
    if not signed_url:
        raise ReportStorageError("The document could not be prepared for download.")
    if signed_url.startswith("https://") or signed_url.startswith("http://"):
        return signed_url
    base_url, _, _ = _storage_configuration()
    if signed_url.startswith("/storage/v1/"):
        return f"{base_url}{signed_url}"
    if signed_url.startswith("/"):
        return f"{base_url}/storage/v1{signed_url}"
    return f"{base_url}/storage/v1/{signed_url.lstrip('/')}"


def new_report_object_path(*, session_id, enrollment_id, section_id, extension):
    suffix = extension.lstrip(".").lower()
    if suffix not in {"pdf", "docx"}:
        raise ValidationError("The uploaded document format is not supported.")
    return (
        f"{session_id}/{enrollment_id}/{section_id}/"
        f"{uuid.uuid4().hex}.{suffix}"
    )
