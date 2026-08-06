from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import now_utc

METRIC_LABELS = {
    "samples": "Số sample",
    "retrieval_hit_rate": "Tỉ lệ retrieval trúng",
    "mean_token_f1": "Token F1 trung bình",
    "judge_accuracy": "Độ chính xác theo LLM judge",
    "mean_judge_score": "Điểm judge trung bình",
}

RAGAS_LABELS = {
    "total_samples": "Tổng số mẫu",
    "answer_relevancy": "Mức liên quan của câu trả lời",
    "answer_relevancy_n": "— số mẫu chấm được",
    "context_precision": "Độ chính xác ngữ cảnh",
    "context_precision_n": "— số mẫu chấm được",
    "context_recall": "Độ bao phủ ngữ cảnh",
    "context_recall_n": "— số mẫu chấm được",
    "faithfulness": "Mức trung thành với ngữ cảnh",
    "faithfulness_n": "— số mẫu chấm được",
}

SOURCE_LABELS = {
    "source": "Nguồn dữ liệu",
    "query": "Câu truy vấn",
    "filter": "Bộ lọc",
    "raw_records": "Số bản ghi thô",
    "clean_records": "Số bản ghi sau làm sạch",
    "max_results": "Giới hạn bản ghi",
    "freshness_threshold_days": "Ngưỡng freshness (ngày)",
    "top_k": "Retrieval top-k",
    "embedding_model": "Mô hình embedding",
    "collection_name": "Tên collection",
}

FRESHNESS_LABELS = {
    "latest_published": "Ngày xuất bản mới nhất",
    "oldest_published": "Ngày xuất bản cũ nhất",
    "stale_rows": "Số dòng quá hạn",
    "total_rows": "Tổng số dòng",
    "is_fresh": "Còn tươi mới",
    "freshness_threshold_days": "Ngưỡng freshness (ngày)",
    "max_age_days": "Tuổi lớn nhất (ngày)",
    "min_age_days": "Tuổi nhỏ nhất (ngày)",
    "mean_age_days": "Tuổi trung bình (ngày)",
    "missing_published": "Số dòng thiếu ngày xuất bản",
    "generated_at": "Thời điểm tạo",
    "report_path": "Đường dẫn report",
}

STATUS_PASS = "ĐẠT"
STATUS_FAIL = "**KHÔNG ĐẠT**"
STATUS_FRESH = "CÒN MỚI"
STATUS_STALE = "QUÁ HẠN"
STATUS_NA = "không có dữ liệu"

def _write_utf8(path: Path | str, content: str) -> None:
    """Ghi file luôn bằng UTF-8.

    Bắt buộc chỉ định encoding: trên Windows ``open(..., "w")`` mặc định dùng
    codepage hệ thống (thường cp1252) và sẽ ném ``UnicodeEncodeError`` ngay khi
    gặp ký tự tiếng Việt có dấu.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relative_path(value: Any) -> str:
    """Rút đường dẫn tuyệt đối về tương đối so với project root.

    Report được commit lên Git nên không được chứa path riêng của máy build.
    """
    if not value:
        return STATUS_NA
    # Chuẩn hoá dấu gạch ngược của Windows trước khi tách: nếu chạy trên Linux,
    # Path("E:\\a\\b") coi cả chuỗi là MỘT phần tử và path tuyệt đối lọt qua nguyên vẹn.
    parts = [p for p in str(value).replace("\\", "/").split("/") if p not in ("", ".")]
    for anchor in ("data", "src", "script"):
        if anchor in parts:
            idx = len(parts) - 1 - parts[::-1].index(anchor)
            return "/".join(parts[idx:])
    return parts[-1] if parts else STATUS_NA


def _format_value(value: Any) -> str:
    if value is None:
        return STATUS_NA
    if isinstance(value, bool):
        return "có" if value else "không"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "-"
    return str(value)


def _format_delta(new: Any, base: Any, digits: int = 4) -> str:
    """Δ có dấu; trả về '-' khi thiếu dữ liệu để không bịa số 0."""
    if not isinstance(new, (int, float)) or not isinstance(base, (int, float)):
        return "-"
    diff = float(new) - float(base)
    if abs(diff) < 10 ** (-digits):
        return "0"
    return f"{diff:+.{digits}f}"


def _kv_table(payload: dict[str, Any], labels: dict[str, str] | None = None) -> list[str]:
    labels = labels or {}
    lines = ["| Mục | Giá trị |", "| --- | --- |"]
    for key, value in payload.items():
        if isinstance(value, (dict, list)) and key not in {"failed_checks"}:
            continue
        label = labels.get(key, key)
        shown = _relative_path(value) if key.endswith("_path") else _format_value(value)
        lines.append(f"| {label} | {shown} |")
    return lines


def _quality_is_pass(quality: dict[str, Any] | None) -> bool | None:
    """None nghĩa là không có payload — khác hẳn với 'không đạt'."""
    if not quality:
        return None
    if "success" in quality:
        return bool(quality["success"])
    checks = quality.get("checks", [])
    if not checks:
        return None
    return quality.get("passed", 0) == len(checks)


def _quality_status(quality: dict[str, Any] | None) -> str:
    result = _quality_is_pass(quality)
    if result is None:
        return STATUS_NA
    return STATUS_PASS if result else STATUS_FAIL


def _quality_ratio(quality: dict[str, Any] | None) -> str:
    if not quality:
        return STATUS_NA
    checks = quality.get("checks", [])
    return f"{quality.get('passed', '?')}/{len(checks)}"


def _fresh_status(freshness: dict[str, Any] | None) -> str:
    if not freshness or "is_fresh" not in freshness:
        return STATUS_NA
    return STATUS_FRESH if freshness["is_fresh"] else STATUS_STALE


def _quality_section(quality: dict[str, Any]) -> list[str]:
    checks = quality.get("checks", [])
    lines = [
        f"- Kết quả tổng: **{_quality_status(quality)}** ({_quality_ratio(quality)} check đạt)",
        f"- Tổng số dòng: {_format_value(quality.get('total_rows'))}",
        f"- Report: `{_relative_path(quality.get('report_path'))}`",
        "",
        "| Check | Kết quả | Quan sát được | Kỳ vọng | Chi tiết |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        mark = STATUS_PASS if check.get("success") else STATUS_FAIL
        lines.append(
            f"| `{check.get('name')}` | {mark} | {_format_value(check.get('observed'))} "
            f"| {check.get('expected', '')} | {check.get('details', '')} |"
        )
    return lines


def _ragas_block(metrics: dict[str, Any]) -> list[str]:
    """Khối Ragas cho phase-1 report; bỏ qua `per_sample` vì quá dài."""
    ragas = metrics.get("ragas")
    if not isinstance(ragas, dict):
        return []
    if "skipped" in ragas:
        return [f"> Ragas: đã bỏ qua — {ragas['skipped']}", ""]
    if "error" in ragas:
        return [f"> Ragas: lỗi — {ragas['error']}", ""]
    shown = {k: v for k, v in ragas.items() if not isinstance(v, (dict, list))}
    if not shown:
        return []
    return ["**Chỉ số Ragas**", "", *_kv_table(shown, RAGAS_LABELS), ""]


def _ragas_value(metrics: dict[str, Any], key: str) -> Any:
    ragas = metrics.get("ragas")
    if isinstance(ragas, dict) and not {"error", "skipped"} & set(ragas):
        return ragas.get(key)
    return None

def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viết markdown report cho baseline phase từ artifact thật.

    Mọi con số trong report đều đọc từ payload được truyền vào
    (metrics/quality/freshness JSON), không hard-code, để report luôn khớp artifact.
    """
    lines: list[str] = [
        "# Phase 1 — Báo cáo Baseline",
        "",
        f"Thời điểm tạo: {now_utc().isoformat()}",
        "",
        "## 1. Nguồn dữ liệu và phạm vi",
        "",
        *_kv_table(source_summary, SOURCE_LABELS),
        "",
        "## 2. Chỉ số đánh giá",
        "",
        *_kv_table({key: metrics.get(key) for key in METRIC_LABELS if key in metrics}, METRIC_LABELS),
        "",
        *_ragas_block(metrics),
        "## 3. Chất lượng dữ liệu",
        "",
        *_quality_section(quality),
        "",
        "## 4. Độ tươi mới của dữ liệu",
        "",
        *_kv_table(freshness, FRESHNESS_LABELS),
        "",
        "## 5. Bằng chứng và giới hạn",
        "",
        "- Chỉ số đọc từ artifact JSON do evaluator ghi ra; report này không tính lại số liệu.",
        "- Cần kiểm tra `judge.reasoning` trong file answers: nếu là fallback heuristic thì "
        "`judge_accuracy` không phải LLM judge và không được trình bày như metric thật.",
        "- Test set được khoá và dùng lại nguyên vẹn cho corrupted và repaired.",
        "- Chỉ số Ragas kèm hậu tố `_n` là số mẫu thực sự chấm được; nếu `_n` nhỏ hơn tổng số mẫu "
        "thì giá trị trung bình đang tính trên mẫu số nhỏ hơn và không so sánh trực tiếp được.",
        "",
    ]

    _write_utf8(report_path, "\n".join(lines))

def generate_corruption_report(
    report_path: Path | str,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
) -> None:
    """Viết markdown so sánh ba trạng thái baseline / corrupted / repaired.

    ``baseline_quality`` và ``baseline_freshness`` là tuỳ chọn để không phá caller cũ,
    nhưng NÊN truyền vào: nếu thiếu, cột baseline của hai dòng observability sẽ ghi
    "không có dữ liệu" thay vì mặc định là đạt.
    """
    rows: list[tuple[str, str, str, int]] = [
        ("Retrieval", "retrieval_hit_rate", "Tỉ lệ retrieval trúng", 4),
        ("Tương đồng", "mean_token_f1", "Token F1 trung bình", 4),
        ("LLM judge", "judge_accuracy", "Độ chính xác theo judge", 4),
        ("LLM judge", "mean_judge_score", "Điểm judge trung bình", 2),
    ]

    table = [
        "| Nhóm | Chỉ số | Baseline | Corrupted | Repaired | Δ do hỏng dữ liệu | Δ sau sửa chữa | Trạng thái |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    unrecovered: list[str] = []

    for group, key, label, digits in rows:
        base = baseline_metrics.get(key)
        corr = corrupted_metrics.get(key)
        rep = repaired_metrics.get(key)

        d_corr = _format_delta(corr, base, digits)
        d_rep = _format_delta(rep, base, digits)

        if not isinstance(base, (int, float)) or not isinstance(rep, (int, float)):
            status = STATUS_NA
        elif rep < base:
            status = "**Chưa phục hồi hết**"
            unrecovered.append(f"`{key}`: repaired {rep:.4f} vẫn thấp hơn baseline {base:.4f} ({d_rep})")
        elif rep > base:
            status = "Cao hơn baseline"
            unrecovered.append(
                f"`{key}`: repaired {rep:.4f} **cao hơn** baseline {base:.4f} ({d_rep}) — "
                "cần kiểm tra xem đây là nhiễu đo lường hay dữ liệu đã đổi"
            )
        else:
            status = "Suy giảm → phục hồi hoàn toàn" if isinstance(corr, (int, float)) and corr < base else "Không đổi"

        table.append(
            f"| {group} | {label} | {_format_value(base)} | {_format_value(corr)} | "
            f"{_format_value(rep)} | {d_corr} | {d_rep} | {status} |"
        )

    # Hai dòng observability — cột baseline lấy từ payload, không hard-code.
    table.append(
        f"| Observability | Chất lượng dữ liệu | {_quality_status(baseline_quality)} | "
        f"{_quality_status(corrupted_quality)} | {_quality_status(repaired_quality)} | - | - | "
        f"{_quality_ratio(baseline_quality)} → {_quality_ratio(corrupted_quality)} → {_quality_ratio(repaired_quality)} |"
    )
    table.append(
        f"| Observability | Độ tươi mới | {_fresh_status(baseline_freshness)} | "
        f"{_fresh_status(corrupted_freshness)} | {_fresh_status(repaired_freshness)} | - | - | "
        f"số dòng quá hạn: {_format_value((baseline_freshness or {}).get('stale_rows'))} → "
        f"{_format_value((corrupted_freshness or {}).get('stale_rows'))} → "
        f"{_format_value((repaired_freshness or {}).get('stale_rows'))} |"
    )

    # Bảng Ragas — chỉ in khi cả ba trạng thái đều có số liệu.
    ragas_keys = [
        ("answer_relevancy", "Mức liên quan của câu trả lời"),
        ("context_precision", "Độ chính xác ngữ cảnh"),
        ("context_recall", "Độ bao phủ ngữ cảnh"),
        ("faithfulness", "Mức trung thành với ngữ cảnh"),
    ]
    ragas_lines: list[str] = []
    ragas_rows = []
    ragas_unrecovered: list[str] = []
    for key, label in ragas_keys:
        base = _ragas_value(baseline_metrics, key)
        corr = _ragas_value(corrupted_metrics, key)
        rep = _ragas_value(repaired_metrics, key)
        if base is None and corr is None and rep is None:
            continue
        n_base = _ragas_value(baseline_metrics, f"{key}_n")
        n_corr = _ragas_value(corrupted_metrics, f"{key}_n")
        n_rep = _ragas_value(repaired_metrics, f"{key}_n")
        note = ""
        if len({n for n in (n_base, n_corr, n_rep) if n is not None}) > 1:
            note = f"mẫu số lệch: {n_base} / {n_corr} / {n_rep}"
        ragas_rows.append(
            f"| {label} | {_format_value(base)} | {_format_value(corr)} | {_format_value(rep)} | "
            f"{_format_delta(corr, base)} | {_format_delta(rep, base)} | {note} |"
        )
        if isinstance(base, (int, float)) and isinstance(rep, (int, float)) and base != rep:
            ragas_unrecovered.append(
                f"`{key}`: repaired {rep:.4f} so với baseline {base:.4f} "
                f"({_format_delta(rep, base)})"
            )
    if ragas_rows:
        ragas_lines = [
            "### Chỉ số Ragas",
            "",
            "| Chỉ số | Baseline | Corrupted | Repaired | Δ do hỏng dữ liệu | Δ sau sửa chữa | Ghi chú |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
            *ragas_rows,
            "",
            "> Chỉ số nào có mẫu số lệch giữa ba trạng thái thì không so sánh trực tiếp được — "
            "phần chênh lệch có thể chỉ do số mẫu bị loại khác nhau.",
            "",
        ]

    if unrecovered:
        recovery_lines = [
            "Các chỉ số chính **chưa** trở lại đúng mức baseline:",
            "",
            *[f"- {item}" for item in unrecovered],
            "",
            "Không được kết luận \"đã phục hồi hoàn toàn\" khi những dòng trên còn tồn tại.",
            "",
        ]
    else:
        recovery_lines = [
            "Bốn chỉ số chính (retrieval, token F1, judge) ở trạng thái repaired đều trở lại "
            "đúng bằng baseline (Δ = 0).",
            "",
            "Kết quả này là kỳ vọng được chứ không phải may mắn: raw snapshot còn nguyên và cleaning "
            "là hàm thuần, nên làm sạch lại từ raw bắt buộc phải cho ra đúng dataset ban đầu. "
            "Nếu Δ ≠ 0 thì mới là dấu hiệu cleaning không tái lập được.",
            "",
        ]

    if ragas_unrecovered:
        ragas_recovery_lines = [
            "Riêng các chỉ số Ragas **chưa** khớp lại với baseline:",
            "",
            *[f"- {item}" for item in ragas_unrecovered],
            "",
            "Cần đọc phần này thận trọng. Baseline và repaired được sinh từ cùng một dataset nên "
            "câu trả lời giống hệt nhau; mọi chênh lệch còn lại đến từ tầng LLM bên trong Ragas "
            "chứ không phải từ pipeline. Đây là **thước đo sàn nhiễu**: thay đổi nhỏ hơn mức "
            "chênh lệch này ở các lần đo khác đều không kết luận được điều gì.",
            "",
        ]
    else:
        ragas_recovery_lines = [
            "Các chỉ số Ragas cũng khớp lại đúng bằng baseline.",
            "",
        ]

    lines = [
        "# Phase 2 — Báo cáo hỏng dữ liệu, quan sát và khả năng phục hồi",
        "",
        f"Thời điểm tạo: {now_utc().isoformat()}",
        "",
        "## 1. Tóm tắt",
        "",
        "Báo cáo đo tác động của việc hỏng dữ liệu lên chất lượng RAG agent và kiểm chứng mức phục hồi "
        "sau khi chạy lại quy trình làm sạch từ dữ liệu thô. Cả ba trạng thái dùng **cùng một test set "
        "đã khoá**, cùng evaluator và cùng `top_k`; nếu không, phần chênh lệch sẽ phản ánh việc đổi "
        "đề bài chứ không phải tác động của dữ liệu.",
        "",
        "---",
        "",
        "## 2. So sánh chỉ số",
        "",
        *table,
        "",
        *ragas_lines,
        "---",
        "",
        "## 3. Mức phục hồi",
        "",
        *recovery_lines,
        *ragas_recovery_lines,
        "---",
        "",
        "## 4. Bằng chứng và giới hạn",
        "",
        "- Mọi con số đọc từ `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` "
        "và các file quality/freshness tương ứng; report không tự tính lại.",
        "- Chuỗi nhân quả đầy đủ cần đối chiếu thêm `corruption_log.json` (loại lỗi, record ID, "
        "before/after) và so cùng một `id` giữa `baseline_answers.json` và `corrupted_answers.json`.",
        "- Chỉ số suy giảm chứng minh corruption có tác động; chỉ số **không đổi** không chứng minh hệ "
        "thống bền — có thể loại corruption đó chưa chạm tới đường đi retrieval → metadata.",
        "",
        "Report do pipeline sinh tự động.",
    ]

    _write_utf8(report_path, "\n".join(lines))