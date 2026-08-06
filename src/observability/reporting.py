from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import now_utc, write_text

METRIC_LABELS = {
    "samples": "So sample",
    "retrieval_hit_rate": "Retrieval hit rate",
    "mean_token_f1": "Mean token F1",
    "judge_accuracy": "Judge accuracy",
    "mean_judge_score": "Mean judge score",
}


def _format_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "-"
    return str(value)


def _kv_table(payload: dict[str, Any], labels: dict[str, str] | None = None) -> list[str]:
    labels = labels or {}
    lines = ["| Field | Value |", "| --- | --- |"]
    for key, value in payload.items():
        if isinstance(value, (dict, list)) and key not in {"failed_checks"}:
            continue
        lines.append(f"| `{labels.get(key, key)}` | {_format_value(value)} |")
    return lines


def _quality_section(quality: dict[str, Any]) -> list[str]:
    checks = quality.get("checks", [])
    status = "PASS" if quality.get("success") else "FAIL"
    lines = [
        f"- Ket qua tong: **{status}** ({quality.get('passed', '?')}/{len(checks)} check pass)",
        f"- Total rows: {_format_value(quality.get('total_rows'))}",
        f"- Report: `{quality.get('report_path', 'n/a')}`",
        "",
        "| Check | Ket qua | Observed | Expected | Chi tiet |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        mark = "PASS" if check.get("success") else "**FAIL**"
        lines.append(
            f"| `{check.get('name')}` | {mark} | {_format_value(check.get('observed'))} "
            f"| {check.get('expected', '')} | {check.get('details', '')} |"
        )
    return lines


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase tu artifact that.

    Moi con so trong report deu doc tu payload duoc truyen vao (metrics/quality/freshness JSON),
    khong hard-code, de report luon khop artifact.
    """
    lines: list[str] = [
        "# Phase 1 - Baseline Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "## 1. Source & scope",
        "",
        *_kv_table(source_summary),
        "",
        "## 2. Evaluation metrics",
        "",
        *_kv_table({key: metrics.get(key) for key in METRIC_LABELS if key in metrics}, METRIC_LABELS),
        "",
    ]

    ragas = metrics.get("ragas")
    if isinstance(ragas, dict):
        if "skipped" in ragas:
            lines += [f"> Ragas: skipped - {ragas['skipped']}", ""]
        elif "error" in ragas:
            lines += [f"> Ragas: error - {ragas['error']}", ""]
        else:
            lines += _kv_table(ragas) + [""]

    lines += [
        "## 3. Data quality",
        "",
        *_quality_section(quality),
        "",
        "## 4. Freshness",
        "",
        *_kv_table(freshness),
        "",
        "## 5. Evidence & limitations",
        "",
        "- Metrics doc tu artifact JSON do evaluator ghi ra; report nay khong tinh lai so lieu.",
        "- Kiem tra `judge.reasoning` trong answers: neu la fallback heuristic thi `judge_accuracy` "
        "khong phai LLM judge.",
        "- Test set duoc khoa va dung lai nguyen ven cho corrupted/repaired.",
        "",
    ]

    _write_with_relative_paths(Path(report_path), lines)


def _write_with_relative_paths(report_path: Path, lines: list[str]) -> None:
    """Ghi report, doi path tuyet doi cua may hien tai thanh path tuong doi so voi project root.

    Report duoc commit len Git nen khong duoc chua path rieng cua may nguoi chay.
    """
    text = "\n".join(lines)
    resolved = report_path.resolve()
    if len(resolved.parents) >= 3:
        project_root = resolved.parents[2]  # <root>/data/reports/<file>.md
        for prefix in (f"{project_root}\\", f"{project_root}/"):
            text = text.replace(prefix, "")
    write_text(report_path, text)


COMPARISON_METRICS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _delta(value: Any, reference: Any) -> str:
    if not isinstance(value, (int, float)) or not isinstance(reference, (int, float)):
        return "n/a"
    diff = value - reference
    if abs(diff) < 1e-9:
        return "0"
    return f"{diff:+.3f}"


def _quality_line(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "n/a"
    checks = payload.get("checks", [])
    return f"{payload.get('passed', '?')}/{len(checks)} pass"


def _failed_line(payload: dict[str, Any] | None) -> str:
    if not payload:
        return "n/a"
    failed = payload.get("failed_checks") or []
    return ", ".join(f"`{name}`" for name in failed) if failed else "-"


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
    corruption_log: Any = None,
    probe_results: dict[str, dict[str, Any]] | None = None,
    judge_integrity: dict[str, dict[str, int]] | None = None,
) -> None:
    """Viet markdown so sanh baseline / corrupted / repaired tu artifact that.

    Cac tham so baseline_quality, baseline_freshness, corruption_log va probe_results la tuy chon:
    khong co thi cot tuong ung hien `n/a` thay vi lam hong report.
    Recovery chi duoc goi la hoan toan khi moi delta repaired-baseline bang 0.
    """
    lines: list[str] = [
        "# Corruption Impact Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "## 1. Metric ba trang thai",
        "",
        "| Metric | Baseline | Corrupted | Repaired | d(corrupted-baseline) | d(repaired-baseline) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    unrecovered: list[str] = []
    unchanged_by_corruption: list[str] = []
    for name in COMPARISON_METRICS:
        base = baseline_metrics.get(name)
        corrupt = corrupted_metrics.get(name)
        repair = repaired_metrics.get(name)
        lines.append(
            f"| `{name}` | {_format_value(base)} | {_format_value(corrupt)} | {_format_value(repair)} "
            f"| {_delta(corrupt, base)} | {_delta(repair, base)} |"
        )
        if _delta(repair, base) not in {"0", "n/a"}:
            unrecovered.append(name)
        if _delta(corrupt, base) == "0":
            unchanged_by_corruption.append(name)

    lines += [
        "",
        f"So sample: baseline {baseline_metrics.get('samples')} / corrupted {corrupted_metrics.get('samples')} "
        f"/ repaired {repaired_metrics.get('samples')} (phai bang nhau -- cung mot test set da khoa).",
        "",
    ]

    if judge_integrity:
        degraded = {state: value for state, value in judge_integrity.items() if value.get("fallback", 0) > 0}
        lines += [
            "### Do tin cay cua judge metric",
            "",
            "| Trang thai | Judge LLM that | Fallback heuristic |",
            "| --- | ---: | ---: |",
        ]
        for state, value in judge_integrity.items():
            total = value.get("total", 0)
            fallback = value.get("fallback", 0)
            lines.append(f"| {state} | {total - fallback}/{total} | {fallback}/{total} |")
        lines.append("")
        if degraded:
            lines += [
                "> **Canh bao:** LLM judge da that bai o "
                + ", ".join(f"`{state}` ({value['fallback']}/{value['total']} sample)" for state, value in degraded.items())
                + " va `_judge_answer` tu dong chuyen sang heuristic dua tren token_f1 ma khong bao loi. "
                "`judge_accuracy` va `mean_judge_score` giua cac trang thai KHONG so sanh duoc; "
                "chi dung `retrieval_hit_rate`, `mean_token_f1` va probe metric (deu khong can LLM) de ket luan.",
                "",
            ]

    if probe_results:
        lines += [
            "### Probe set (do rieng tang retrieval, khong dung exact lookup)",
            "",
            "| Metric | Baseline | Corrupted | Repaired |",
            "| --- | ---: | ---: | ---: |",
        ]
        probe_keys = ["top1_accuracy", "mrr"]
        sample_state = next(iter(probe_results.values()), {})
        probe_keys += [key for key in sample_state if key.startswith("retrieval_hit_rate_at_")]
        for key in probe_keys:
            row = [_format_value((probe_results.get(state) or {}).get(key)) for state in ("baseline", "corrupted", "repaired")]
            lines.append(f"| `{key}` | {row[0]} | {row[1]} | {row[2]} |")
        lines.append("")

    lines += [
        "## 2. Data quality signals",
        "",
        "| Trang thai | Ket qua | Rows | Check fail |",
        "| --- | --- | ---: | --- |",
        f"| Baseline | {_quality_line(baseline_quality)} | {_format_value((baseline_quality or {}).get('total_rows'))} | {_failed_line(baseline_quality)} |",
        f"| Corrupted | {_quality_line(corrupted_quality)} | {_format_value(corrupted_quality.get('total_rows'))} | {_failed_line(corrupted_quality)} |",
        f"| Repaired | {_quality_line(repaired_quality)} | {_format_value(repaired_quality.get('total_rows'))} | {_failed_line(repaired_quality)} |",
        "",
        "## 3. Freshness",
        "",
        "| Trang thai | is_fresh | stale_rows | latest_published | max_age_days |",
        "| --- | --- | ---: | --- | ---: |",
    ]
    for label, payload in (
        ("Baseline", baseline_freshness),
        ("Corrupted", corrupted_freshness),
        ("Repaired", repaired_freshness),
    ):
        payload = payload or {}
        lines.append(
            f"| {label} | {_format_value(payload.get('is_fresh'))} | {_format_value(payload.get('stale_rows'))} "
            f"| {_format_value(payload.get('latest_published'))} | {_format_value(payload.get('max_age_days'))} |"
        )
    lines.append("")

    if corruption_log:
        entries = corruption_log if isinstance(corruption_log, list) else corruption_log.get("entries", [])
        lines += ["## 4. Corruption log", ""]
        if entries:
            keys = [key for key in ("type", "paper_id", "parameter", "before", "after", "rows_before", "rows_after") if any(key in entry for entry in entries)]
            lines += ["| " + " | ".join(keys) + " |", "| " + " | ".join("---" for _ in keys) + " |"]
            for entry in entries:
                lines.append("| " + " | ".join(_format_value(entry.get(key)) for key in keys) + " |")
        else:
            lines.append("Corruption log rong.")
        lines.append("")

    section = "5" if corruption_log else "4"
    lines += [
        f"## {section}. Doc ket qua",
        "",
        "**Recovery**: "
        + (
            "hoan toan -- moi metric repaired bang baseline."
            if not unrecovered
            else "**chua hoan toan** -- cac metric sau chua ve muc baseline: "
            + ", ".join(f"`{name}`" for name in unrecovered)
            + "."
        ),
        "",
        "**Signal khong doi sau corruption**: "
        + (
            ", ".join(f"`{name}`" for name in unchanged_by_corruption)
            + ". Metric giu nguyen KHONG chung minh he thong ben vung -- chi nghia la corruption do "
            "chua cham toi duong di retrieval -> metadata ma metric nay do."
            if unchanged_by_corruption
            else "khong co -- moi metric deu thay doi."
        ),
        "",
        "**Gioi han cua ket luan**:",
        "",
        f"- Test set chi co {baseline_metrics.get('samples', '?')} sample, moi sample sai lam metric doi dang ke; "
        "khong suy rong ra ngoai corpus nay.",
        "- Metric o bang 1 duoc tinh boi evaluator tren cung mot test set da khoa cho ca ba trang thai.",
        "- Kiem `judge.reasoning` trong answers: neu la fallback heuristic thi `judge_accuracy` khong phai LLM judge.",
        "",
    ]

    _write_with_relative_paths(Path(report_path), lines)
