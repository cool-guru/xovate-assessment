import io
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

REQUIRED_COLUMNS = ["id", "email", "age"]
MIN_DATA_ROWS = 11
MIN_AGE = 18
MAX_AGE = 100

app = FastAPI(
    title="Xovate Data Validation API",
    description="Uploads a CSV file and validates the required columns.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _strip_wrapped_quotes(raw_text: str) -> str:
    """Remove leading/trailing quotes that wrap entire CSV rows."""
    sanitized_lines: List[str] = []
    for line in raw_text.splitlines():
        stripped_line = line.lstrip("\ufeff")
        if stripped_line.startswith('"') and stripped_line.endswith('"'):
            sanitized_lines.append(stripped_line[1:-1])
        else:
            sanitized_lines.append(stripped_line)
    return "\n".join(sanitized_lines)


def _normalize_blank(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text_value = str(value).strip()
    return text_value or None


def _safe_row_id(raw_id: Any) -> Optional[int]:
    normalized = _normalize_blank(raw_id)
    if normalized is None:
        return None
    try:
        return int(normalized)
    except ValueError:
        return None


def _load_dataframe(file_bytes: bytes) -> pd.DataFrame:
    text_content = file_bytes.decode("utf-8-sig")
    attempts = [text_content]
    sanitized = _strip_wrapped_quotes(text_content)
    if sanitized != text_content:
        attempts.append(sanitized)

    last_error: Optional[Exception] = None
    fallback_df: Optional[pd.DataFrame] = None

    for candidate in attempts:
        try:
            df = pd.read_csv(io.StringIO(candidate), dtype=str)
        except Exception as exc:  # pragma: no cover - defensive parse guard
            last_error = exc
            continue
        df = df.where(pd.notna(df), None)
        if set(REQUIRED_COLUMNS).issubset(df.columns):
            return df
        if fallback_df is None:
            fallback_df = df

    if fallback_df is not None:
        return fallback_df

    raise HTTPException(status_code=400, detail=f"Unable to parse CSV file: {last_error}")


def _volume_check(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    if len(df.index) < MIN_DATA_ROWS:
        return {
            "row_index": None,
            "id": None,
            "column": "_file",
            "error_message": "The file must contain more than 10 data rows.",
        }
    return None


def _email_errors(df: pd.DataFrame) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for row_idx, value in df["email"].items():
        if _normalize_blank(value) is None:
            errors.append(
                {
                    "row_index": row_idx + 1,
                    "id": _safe_row_id(df.at[row_idx, "id"]),
                    "column": "email",
                    "error_message": "Email is required and cannot be blank.",
                }
            )
    return errors


def _age_errors(df: pd.DataFrame) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for row_idx, value in df["age"].items():
        normalized = _normalize_blank(value)
        row_id = _safe_row_id(df.at[row_idx, "id"])
        if normalized is None:
            errors.append(
                {
                    "row_index": row_idx + 1,
                    "id": row_id,
                    "column": "age",
                    "error_message": "Invalid age format: value is missing.",
                }
            )
            continue

        if normalized.lstrip("+-").isdigit():
            age_value = int(normalized)
        else:
            errors.append(
                {
                    "row_index": row_idx + 1,
                    "id": row_id,
                    "column": "age",
                    "error_message": f"Invalid age format: '{normalized}'.",
                }
            )
            continue

        if age_value < MIN_AGE or age_value > MAX_AGE:
            errors.append(
                {
                    "row_index": row_idx + 1,
                    "id": row_id,
                    "column": "age",
                    "error_message": f"Age {age_value} is outside the allowed range {MIN_AGE}-{MAX_AGE}.",
                }
            )
    return errors


@app.post("/validate")
async def validate(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV uploads are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    df = _load_dataframe(file_bytes)

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        errors = [
            {
                "row_index": None,
                "id": None,
                "column": column,
                "error_message": f"Required column '{column}' is missing.",
            }
            for column in missing_columns
        ]
        return {"status": "fail", "errors": errors}

    volume_error = _volume_check(df)
    if volume_error:
        return {"status": "fail", "errors": [volume_error]}

    errors: List[Dict[str, Any]] = []
    errors.extend(_email_errors(df))
    errors.extend(_age_errors(df))

    status = "pass" if not errors else "fail"
    return {"status": status, "errors": errors}
