from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, read_json, safe_slug, write_json

MIN_ROW_COUNT = 10
MIN_SUMMARY_CHARS = 100

REQUIRED_COLUMNS = (
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
    "age_days",
    "text_for_embedding",
)


def _check(name: str, success: bool, observed: Any, expected: str, details: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "success": bool(success),
        "observed": observed,
        "expected": expected,
        "details": details,
    }


def _missing_mask(series: pd.Series) -> pd.Series:
    """Null, NaN hoac chuoi rong sau khi strip deu tinh la missing."""
    blank = series.astype("string").fillna("").str.strip() == ""
    return series.isna() | blank


def _parse_published(df: pd.DataFrame) -> pd.Series:
    """Parse cot `published`; gia tri khong parse duoc (vd partial date `2026-07`) thanh NaT."""
    if "published" not in df.columns:
        return pd.Series(pd.NaT, index=df.index)
    return pd.to_datetime(df["published"], errors="coerce", utc=True, format="mixed")


def _offending_ids(df: pd.DataFrame, mask: pd.Series, limit: int = 5) -> list[str]:
    if "paper_id" not in df.columns:
        return []
    return df.loc[mask, "paper_id"].astype(str).tolist()[:limit]


def _missing_check(df: pd.DataFrame, column: str, name: str) -> dict[str, Any]:
    if column not in df.columns:
        return _check(name, False, "column missing", f"cot `{column}` ton tai", f"Cleaned dataframe khong co cot `{column}`.")
    missing = _missing_mask(df[column])
    count = int(missing.sum())
    ids = df.loc[missing, "paper_id"].astype(str).tolist() if "paper_id" in df.columns else []
    return _check(
        name,
        count == 0,
        count,
        "0 missing",
        "" if count == 0 else f"{count}/{len(df)} row thieu `{column}`: {ids[:5]}",
    )


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks tren cleaned dataframe va ghi JSON report.

    Report duoc ghi ra `data/quality/<report_name>_quality.json` nen baseline,
    corrupted va repaired khong ghi de len nhau.
    Check fail khong raise: pipeline van chay tiep de con do duoc impact len metrics.
    """
    total_rows = int(len(df))
    checks: list[dict[str, Any]] = []

    checks.append(
        _check(
            "row_count_min",
            total_rows >= MIN_ROW_COUNT,
            total_rows,
            f">= {MIN_ROW_COUNT} rows",
            "" if total_rows >= MIN_ROW_COUNT else f"Chi co {total_rows} row, thieu du lieu de evaluate on dinh.",
        )
    )

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    checks.append(
        _check(
            "schema_columns_present",
            not missing_columns,
            len(REQUIRED_COLUMNS) - len(missing_columns),
            f"{len(REQUIRED_COLUMNS)} cot bat buoc",
            "" if not missing_columns else f"Thieu cot: {missing_columns}",
        )
    )

    checks.append(_missing_check(df, "paper_id", "paper_id_not_null"))

    if "paper_id" in df.columns:
        duplicated_ids = df.loc[df["paper_id"].duplicated(keep=False), "paper_id"].astype(str).unique().tolist()
        unique_ids = int(df["paper_id"].nunique(dropna=False))
        checks.append(
            _check(
                "paper_id_unique",
                unique_ids == total_rows,
                unique_ids,
                f"{total_rows} unique",
                "" if unique_ids == total_rows else f"paper_id bi trung: {duplicated_ids[:5]}",
            )
        )
    else:
        checks.append(_check("paper_id_unique", False, "column missing", "paper_id unique", "Khong co cot `paper_id`."))

    dedupe_columns = [column for column in ("paper_id", "title", "published") if column in df.columns]
    if dedupe_columns:
        duplicate_rows = int(df.duplicated(subset=dedupe_columns).sum())
        checks.append(
            _check(
                "duplicate_records",
                duplicate_rows == 0,
                duplicate_rows,
                "0 duplicate rows",
                "" if duplicate_rows == 0 else f"{duplicate_rows} row trung tren {dedupe_columns}.",
            )
        )

    checks.append(_missing_check(df, "title", "title_not_null"))
    checks.append(_missing_check(df, "summary", "summary_not_null"))
    checks.append(_missing_check(df, "text_for_embedding", "text_for_embedding_not_empty"))

    if "summary" in df.columns:
        lengths = (
            pd.to_numeric(df["summary_chars"], errors="coerce")
            if "summary_chars" in df.columns
            else df["summary"].astype("string").fillna("").str.len()
        )
        lengths = lengths.fillna(0)
        short_rows = int((lengths < MIN_SUMMARY_CHARS).sum())
        checks.append(
            _check(
                "summary_min_chars",
                short_rows == 0,
                short_rows,
                f"0 row < {MIN_SUMMARY_CHARS} ky tu",
                "" if short_rows == 0 else f"{short_rows}/{total_rows} row co summary ngan hon {MIN_SUMMARY_CHARS} ky tu.",
            )
        )
    else:
        checks.append(_check("summary_min_chars", False, "column missing", f">= {MIN_SUMMARY_CHARS} chars", "Khong co cot `summary`."))

    parsed_published = _parse_published(df)
    unparseable = parsed_published.isna()
    unparseable_count = int(unparseable.sum())
    checks.append(
        _check(
            "published_parseable",
            "published" in df.columns and unparseable_count == 0,
            unparseable_count if "published" in df.columns else "column missing",
            "0 row khong parse duoc ngay",
            ""
            if "published" in df.columns and unparseable_count == 0
            else f"{unparseable_count}/{total_rows} row co `published` rong hoac khong parse duoc: {_offending_ids(df, unparseable)}",
        )
    )

    threshold = settings.freshness_threshold_days
    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
        max_age = int(ages.max()) if ages.notna().any() else None
        # NaN khong so sanh duoc voi threshold nen phai dem rieng, neu khong row thieu ngay se
        # lot qua check freshness mot cach im lang.
        missing_age = int(ages.isna().sum())
        stale_rows = int((ages > threshold).sum())
        details = []
        if stale_rows:
            details.append(f"{stale_rows}/{total_rows} row stale (age_days > {threshold}).")
        if missing_age:
            details.append(f"{missing_age}/{total_rows} row thieu `age_days`: {_offending_ids(df, ages.isna())}.")
        checks.append(
            _check(
                "freshness_age_days",
                stale_rows == 0 and missing_age == 0,
                max_age,
                f"max age_days <= {threshold}, 0 row thieu age_days",
                " ".join(details),
            )
        )
    else:
        checks.append(_check("freshness_age_days", False, "column missing", f"<= {threshold} days", "Khong co cot `age_days`."))

    failed_checks = [check["name"] for check in checks if not check["success"]]
    payload = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "total_rows": total_rows,
        "success": not failed_checks,
        "passed": len(checks) - len(failed_checks),
        "failed": len(failed_checks),
        "checks": checks,
        "failed_checks": failed_checks,
    }

    output_path = settings.paths.quality_dir / f"{safe_slug(report_name)}_quality.json"
    write_json(output_path, payload)
    payload["report_path"] = str(output_path)
    return payload


def audit_index_manifest(settings: Settings, manifest_path: Path, df: pd.DataFrame | None = None) -> dict[str, Any]:
    """Audit embedding manifest: collection name, so document, va khop voi cleaned data.

    Dung de xac minh index that su duoc build tu dung dataset, thay vi tin vao ten collection.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return {
            "manifest_path": str(manifest_path),
            "exists": False,
            "success": False,
            "details": "Chua co embedding manifest -- index chua duoc build.",
        }

    payload = read_json(manifest_path)
    documents = payload.get("documents", [])
    manifest_ids = {str(document.get("paper_id")) for document in documents}

    result: dict[str, Any] = {
        "manifest_path": str(manifest_path),
        "exists": True,
        "backend": payload.get("backend"),
        "embedding_model": payload.get("embedding_model"),
        "collection_name": payload.get("collection_name"),
        "persist_path": payload.get("persist_path"),
        "document_count": len(documents),
        "unique_paper_ids": len(manifest_ids),
    }

    problems: list[str] = []

    # A manifest may only carry a project-relative path. Resolution belongs to
    # the current checkout's settings, so an old absolute path is rejected.
    manifest_persist_value = str(payload.get("persist_path", ""))
    manifest_persist = Path(manifest_persist_value)
    expected_persist = settings.paths.chroma_dir.resolve()
    resolved_manifest_persist = (
        (settings.paths.project_dir / manifest_persist).resolve()
        if not manifest_persist.is_absolute()
        else manifest_persist.resolve()
    )
    result["persist_path_portable"] = (
        bool(manifest_persist_value)
        and not manifest_persist.is_absolute()
        and resolved_manifest_persist == expected_persist
    )
    if not result["persist_path_portable"]:
        problems.append(
            f"persist_path trong manifest (`{manifest_persist_value}`) phai la path tuong doi "
            f"tro toi chroma_dir cua project (`{expected_persist}`)."
        )

    if payload.get("embedding_model") != settings.embedding_model:
        problems.append(f"embedding_model lech: manifest={payload.get('embedding_model')} vs settings={settings.embedding_model}")
    if len(documents) != len(manifest_ids):
        problems.append(f"{len(documents)} document nhung chi {len(manifest_ids)} paper_id -> co document trung.")

    if df is not None and "paper_id" in df.columns:
        clean_ids = set(df["paper_id"].astype(str))
        missing = sorted(clean_ids - manifest_ids)
        extra = sorted(manifest_ids - clean_ids)
        result["clean_rows"] = len(clean_ids)
        result["missing_from_index"] = missing[:5]
        result["extra_in_index"] = extra[:5]
        if missing:
            problems.append(f"{len(missing)} paper_id co trong clean nhung khong co trong index.")
        if extra:
            problems.append(f"{len(extra)} paper_id co trong index nhung khong co trong clean.")

        # paper_id khop khong du: cleaning co the doi noi dung (vd decode HTML entity) ma giu nguyen id.
        # Index cu + clean moi -> answer va ground_truth doc tu hai phien ban khac nhau.
        by_id = {str(record["paper_id"]): record for record in df.to_dict(orient="records")}

        def normalize_content(value: object) -> str:
            return str(value).replace("\r\n", "\n").replace("\r", "\n")

        drifted_title: list[str] = []
        drifted_content: list[str] = []
        for document in documents:
            row = by_id.get(str(document.get("paper_id")))
            if row is None:
                continue
            if normalize_content(document.get("title")) != normalize_content(row.get("title")):
                drifted_title.append(str(document.get("paper_id")))
            if normalize_content(document.get("content")) != normalize_content(row.get("text_for_embedding")):
                drifted_content.append(str(document.get("paper_id")))
        result["content_drift_title"] = drifted_title[:5]
        result["content_drift_text"] = drifted_content[:5]
        if drifted_title or drifted_content:
            problems.append(
                f"Index lech noi dung so voi clean hien tai: {len(drifted_title)} title, "
                f"{len(drifted_content)} text_for_embedding -> can rebuild index tu clean moi."
            )

    result["success"] = not problems
    result["details"] = " ".join(problems)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Tong hop freshness tu `published` va `age_days` da co san trong cleaned data.

    Khong tinh lai tuoi bang `datetime.now()`: `age_days` do cleaning tinh tu `run_date`,
    tinh lai se lam baseline khong tai lap duoc khi chay lai vao ngay khac.
    `report_path` truyen tuong minh de corrupted/repaired khong ghi de baseline.
    """
    total_rows = int(len(df))
    threshold = settings.freshness_threshold_days

    if "published" in df.columns:
        published = pd.to_datetime(df["published"], errors="coerce", utc=True, format="mixed")
    else:
        published = pd.Series(pd.NaT, index=df.index)
    valid_published = published.dropna()
    latest_published = valid_published.max().date().isoformat() if not valid_published.empty else None
    oldest_published = valid_published.min().date().isoformat() if not valid_published.empty else None

    if "age_days" in df.columns:
        ages = pd.to_numeric(df["age_days"], errors="coerce")
    else:
        ages = pd.Series(dtype="float64", index=df.index)
    valid_ages = ages.dropna()
    stale_rows = int((ages > threshold).sum())
    missing_published = int(published.isna().sum())

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": stale_rows == 0 and missing_published == 0 and total_rows > 0,
        "freshness_threshold_days": threshold,
        "max_age_days": int(valid_ages.max()) if not valid_ages.empty else None,
        "min_age_days": int(valid_ages.min()) if not valid_ages.empty else None,
        "mean_age_days": round(float(valid_ages.mean()), 1) if not valid_ages.empty else None,
        "missing_published": missing_published,
        "generated_at": now_utc().isoformat(),
    }

    write_json(Path(report_path), payload)
    payload["report_path"] = str(report_path)
    return payload
