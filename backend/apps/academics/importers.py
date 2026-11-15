import csv
import io
from pathlib import Path
from zipfile import BadZipFile

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .models import (
    RosterImportBatch,
    RosterImportRow,
    RosterImportRowStatus,
    RosterImportStatus,
    RosterRecordSource,
    AcademicSessionStatus,
    StudentRosterRecord,
    normalise_matric_number,
)

MAX_ROSTER_IMPORT_BYTES = 10 * 1024 * 1024
MAX_ROSTER_IMPORT_ROWS = 5000

HEADER_ALIASES = {
    "matric_no": "matric_number",
    "matric_number": "matric_number",
    "matriculation_number": "matric_number",
    "matriculation_no": "matric_number",
    "first_name": "first_name",
    "given_name": "first_name",
    "surname": "last_name",
    "last_name": "last_name",
    "other_names": "other_names",
    "middle_name": "other_names",
    "email": "email",
    "email_address": "email",
    "phone": "phone",
    "phone_number": "phone",
    "is_eligible": "is_eligible",
}
REQUIRED_HEADERS = {"matric_number", "first_name", "last_name"}


def normalise_header(value):
    raw = str(value or "").strip().lower()
    raw = "_".join(raw.replace("-", " ").split())
    return HEADER_ALIASES.get(raw, raw)


def parse_boolean(value):
    if value is None or str(value).strip() == "":
        return True
    normalised = str(value).strip().lower()
    if normalised in {"true", "yes", "1", "eligible"}:
        return True
    if normalised in {"false", "no", "0", "ineligible"}:
        return False
    raise ValueError("is_eligible must be true/false, yes/no or 1/0.")


def _rows_from_csv(content):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("CSV files must use UTF-8 encoding.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValidationError("The CSV file must contain a header row.")
    headers = {normalise_header(header) for header in reader.fieldnames}
    missing = REQUIRED_HEADERS - headers
    if missing:
        raise ValidationError(f"Missing required columns: {', '.join(sorted(missing))}.")
    rows = []
    for row_number, row in enumerate(reader, start=2):
        mapped = {normalise_header(key): value for key, value in row.items() if key}
        rows.append((row_number, mapped))
    return rows


def _rows_from_xlsx(content):
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    worksheet = workbook.active
    iterator = worksheet.iter_rows(values_only=True)
    header_row = next(iterator, None)
    if not header_row:
        raise ValidationError("The spreadsheet must contain a header row.")
    headers = [normalise_header(value) for value in header_row]
    missing = REQUIRED_HEADERS - set(headers)
    if missing:
        raise ValidationError(f"Missing required columns: {', '.join(sorted(missing))}.")
    rows = []
    for row_number, values in enumerate(iterator, start=2):
        mapped = {
            header: value
            for header, value in zip(headers, values)
            if header
        }
        rows.append((row_number, mapped))
    workbook.close()
    return rows


def parse_roster_upload(uploaded_file):
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in {".csv", ".xlsx"}:
        raise ValidationError("Only CSV and XLSX roster files are supported.")
    if uploaded_file.size > MAX_ROSTER_IMPORT_BYTES:
        raise ValidationError("Roster import files must not exceed 10 MB.")

    content = uploaded_file.read()
    try:
        rows = _rows_from_csv(content) if extension == ".csv" else _rows_from_xlsx(content)
    except (BadZipFile, InvalidFileException, KeyError, OSError, EOFError, ValueError) as exc:
        raise ValidationError("The uploaded roster file could not be read. Check that it is a valid CSV or XLSX file.") from exc
    if len(rows) > MAX_ROSTER_IMPORT_ROWS:
        raise ValidationError(f"A roster import cannot contain more than {MAX_ROSTER_IMPORT_ROWS} rows.")
    return rows


def _string_value(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


@transaction.atomic
def preview_roster_import(*, session, uploaded_file, actor):
    if session.status == AcademicSessionStatus.CLOSED:
        raise ValidationError("Roster records cannot be imported into a closed academic session.")
    parsed_rows = parse_roster_upload(uploaded_file)
    if not any(any(_string_value(value) for value in row.values()) for _, row in parsed_rows):
        raise ValidationError("The roster file does not contain any student records.")
    batch = RosterImportBatch.objects.create(
        session=session,
        original_file_name=Path(uploaded_file.name).name[:255],
        uploaded_by=actor,
    )
    existing_matric_numbers = set(
        StudentRosterRecord.objects.filter(session=session).values_list(
            "matric_number", flat=True
        )
    )
    seen_in_upload = set()
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0
    processed_count = 0

    for row_number, raw_data in parsed_rows:
        if not any(_string_value(value) for value in raw_data.values()):
            continue
        processed_count += 1
        matric_number = normalise_matric_number(raw_data.get("matric_number"))
        first_name = _string_value(raw_data.get("first_name"))
        last_name = _string_value(raw_data.get("last_name"))
        other_names = _string_value(raw_data.get("other_names"))
        email = _string_value(raw_data.get("email")).lower()
        phone = _string_value(raw_data.get("phone"))
        errors = []

        if not matric_number:
            errors.append("Matriculation number is required.")
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if len(matric_number) > 40:
            errors.append("Matriculation number cannot exceed 40 characters.")
        if len(first_name) > 150 or len(last_name) > 150 or len(other_names) > 150:
            errors.append("Student names cannot exceed 150 characters per field.")
        if len(email) > 254:
            errors.append("Email address cannot exceed 254 characters.")
        if len(phone) > 30:
            errors.append("Phone number cannot exceed 30 characters.")
        try:
            is_eligible = parse_boolean(raw_data.get("is_eligible"))
        except ValueError as exc:
            is_eligible = True
            errors.append(str(exc))

        if email:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Email address is not valid.")

        row_status = RosterImportRowStatus.VALID
        if errors:
            row_status = RosterImportRowStatus.INVALID
            invalid_count += 1
        elif matric_number in existing_matric_numbers or matric_number in seen_in_upload:
            row_status = RosterImportRowStatus.DUPLICATE
            errors.append("Matriculation number already exists in this session or import file.")
            duplicate_count += 1
        else:
            valid_count += 1
            seen_in_upload.add(matric_number)

        safe_raw_data = {str(key): _string_value(value) for key, value in raw_data.items()}
        RosterImportRow.objects.create(
            batch=batch,
            row_number=row_number,
            raw_data=safe_raw_data,
            matric_number=matric_number[:40],
            first_name=first_name[:150],
            last_name=last_name[:150],
            other_names=other_names[:150],
            email=email[:254],
            phone=phone[:30],
            is_eligible=is_eligible,
            status=row_status,
            errors=errors,
        )

    batch.total_rows = processed_count
    batch.valid_rows = valid_count
    batch.invalid_rows = invalid_count
    batch.duplicate_rows = duplicate_count
    batch.save(
        update_fields=[
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "duplicate_rows",
        ]
    )
    return batch


@transaction.atomic
def commit_roster_import(*, batch_id, actor):
    batch = RosterImportBatch.objects.select_for_update().get(pk=batch_id)
    if batch.status != RosterImportStatus.PREVIEWED:
        raise ValidationError("Only a previewed roster import can be committed.")
    if batch.session.status == AcademicSessionStatus.CLOSED:
        raise ValidationError("Roster imports cannot be committed to a closed academic session.")

    imported_count = 0
    for row in batch.rows.filter(status=RosterImportRowStatus.VALID).order_by("row_number"):
        try:
            with transaction.atomic():
                record = StudentRosterRecord.objects.create(
                    session=batch.session,
                    matric_number=row.matric_number,
                    first_name=row.first_name,
                    last_name=row.last_name,
                    other_names=row.other_names,
                    email=row.email,
                    phone=row.phone,
                    is_eligible=row.is_eligible,
                    source=RosterRecordSource.IMPORT,
                    created_by=actor,
                    updated_by=actor,
                )
            row.created_record = record
            row.save(update_fields=["created_record"])
            imported_count += 1
        except IntegrityError:
            row.status = RosterImportRowStatus.DUPLICATE
            row.errors = ["Matriculation number was added by another import or manual entry after preview."]
            row.save(update_fields=["status", "errors"])
            batch.duplicate_rows += 1
            batch.valid_rows = max(0, batch.valid_rows - 1)

    batch.status = RosterImportStatus.COMMITTED
    batch.imported_rows = imported_count
    batch.committed_at = timezone.now()
    batch.save(
        update_fields=[
            "status",
            "imported_rows",
            "committed_at",
            "duplicate_rows",
            "valid_rows",
        ]
    )
    return batch
